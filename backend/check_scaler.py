import pickle

# Load scaler
with open('ml_models/scaler_X.pkl', 'rb') as f:
    scaler = pickle.load(f)

print(f"Scaler expects {scaler.n_features_in_} features")
print(f"Feature names: {getattr(scaler, 'feature_names_in_', 'Not available')}")

# Check scaler shape
print(f"\nScaler shape: {scaler.scale_.shape}")
print(f"Mean shape: {scaler.mean_.shape}")
