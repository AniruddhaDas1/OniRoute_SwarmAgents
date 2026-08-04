def validate(original, optimized, protected=()):
    return all(key in optimized and optimized[key] == original[key] for key in protected)
