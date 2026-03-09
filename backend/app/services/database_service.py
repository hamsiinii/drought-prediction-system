"""
DynamoDB Database Service for Drought Analytics
Replaces MongoDB with AWS DynamoDB (ap-south-1)
"""

import boto3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import os


def float_to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def decimal_to_float(obj):
    """Recursively convert Decimals back to float for JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


class DatabaseService:
    """AWS DynamoDB service for storing drought predictions"""

    TABLE_NAME = "drought_predictions"
    REGION = os.getenv("AWS_REGION", "ap-south-1")

    def __init__(self):
        self.dynamodb = None
        self.table = None

    async def connect(self):
        """Initialize DynamoDB connection and ensure table exists"""
        try:
            self.dynamodb = boto3.resource(
                "dynamodb",
                region_name=self.REGION,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            await self._ensure_table()
            print(f"✅ Connected to DynamoDB table: {self.TABLE_NAME}")
        except Exception as e:
            print(f"⚠️ DynamoDB connection failed: {e}. Predictions won't be saved.")
            self.table = None

    async def _ensure_table(self):
        """Create DynamoDB table if it doesn't exist"""
        existing = [t.name for t in self.dynamodb.tables.all()]

        if self.TABLE_NAME not in existing:
            print(f"📦 Creating DynamoDB table: {self.TABLE_NAME}")
            table = self.dynamodb.create_table(
                TableName=self.TABLE_NAME,
                KeySchema=[
                    {"AttributeName": "id", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("✅ Table created successfully")

        self.table = self.dynamodb.Table(self.TABLE_NAME)

    async def disconnect(self):
        """No persistent connection to close for DynamoDB"""
        pass

    async def save_prediction(
        self,
        prediction_type: str,
        input_data: List[Dict],
        result: Dict,
        location: Optional[str] = None,
    ):
        """Save a single prediction to DynamoDB"""
        if not self.table:
            return

        try:
            item = {
                "id": str(uuid.uuid4()),
                "prediction_type": prediction_type,
                "location": location or "Unknown",
                "regcdi_value": str(result.get("regcdi_value", 0)),
                "drought_category": result.get("drought_category", "Unknown"),
                "severity_level": result.get("severity_level", "unknown"),
                "confidence_score": str(result.get("confidence_score", 0)),
                "model_version": result.get("model_version", "1.0.0"),
                "created_at": datetime.utcnow().isoformat(),
                "input_summary": json.dumps(float_to_decimal(input_data[:1])),  # store first month as sample
            }

            self.table.put_item(Item=item)
        except Exception as e:
            print(f"⚠️ Failed to save prediction: {e}")

    async def save_batch_predictions(self, filename: str, predictions: List[Dict]):
        """Save batch predictions from CSV upload"""
        if not self.table:
            return

        try:
            with self.table.batch_writer() as batch:
                for pred in predictions:
                    item = {
                        "id": str(uuid.uuid4()),
                        "prediction_type": "batch",
                        "location": filename,
                        "regcdi_value": str(pred.get("regcdi_value", 0)),
                        "drought_category": pred.get("drought_category", "Unknown"),
                        "severity_level": pred.get("severity_level", "unknown"),
                        "confidence_score": str(pred.get("confidence_score", 0)),
                        "model_version": pred.get("model_version", "1.0.0"),
                        "created_at": datetime.utcnow().isoformat(),
                        "input_summary": "{}",
                    }
                    batch.put_item(Item=item)
        except Exception as e:
            print(f"⚠️ Failed to save batch predictions: {e}")

    async def get_prediction_history(
        self, skip: int = 0, limit: int = 50
    ) -> List[Dict]:
        """Get prediction history from DynamoDB"""
        if not self.table:
            return []

        try:
            response = self.table.scan(Limit=limit + skip)
            items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response and len(items) < limit + skip:
                response = self.table.scan(
                    Limit=limit + skip,
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            items = items[skip : skip + limit]

            # Convert Decimals and ensure float types
            result = []
            for item in items:
                item = decimal_to_float(item)
                item["regcdi_value"] = float(item.get("regcdi_value", 0))
                item["confidence_score"] = float(item.get("confidence_score", 0))
                result.append(item)

            # Sort by created_at descending
            result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return result

        except Exception as e:
            print(f"⚠️ Failed to get history: {e}")
            return []

    async def get_recent_predictions(
        self, location: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent predictions optionally filtered by location"""
        history = await self.get_prediction_history(limit=100)

        if location:
            history = [h for h in history if h.get("location") == location]

        return history[:limit]

    async def get_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics from all predictions"""
        if not self.table:
            return self._empty_summary()

        try:
            response = self.table.scan()
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            if not items:
                return self._empty_summary()

            items = [decimal_to_float(i) for i in items]

            regcdi_values = [float(i.get("regcdi_value", 0)) for i in items]
            avg_regcdi = sum(regcdi_values) / len(regcdi_values)

            # Drought distribution
            dist = {}
            for item in items:
                cat = item.get("drought_category", "Unknown").lower().replace(" ", "_")
                dist[cat] = dist.get(cat, 0) + 1

            last_date = max(
                (i.get("created_at", "") for i in items), default="N/A"
            )

            return {
                "total_predictions": len(items),
                "average_regcdi": round(avg_regcdi, 3),
                "drought_distribution": dist,
                "last_prediction_date": last_date,
                "regcdi_values": regcdi_values,
            }

        except Exception as e:
            print(f"⚠️ Failed to get summary: {e}")
            return self._empty_summary()

    def _empty_summary(self):
        return {
            "total_predictions": 0,
            "average_regcdi": 0.0,
            "drought_distribution": {},
            "last_prediction_date": "N/A",
            "regcdi_values": [],
        }
