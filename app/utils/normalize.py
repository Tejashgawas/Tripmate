def normalize_to_dict(obj):
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, 'dict'):
        return obj.dict()
    return obj