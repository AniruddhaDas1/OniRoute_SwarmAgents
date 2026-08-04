class ModelLayerError(Exception): pass
class ModelNotFoundError(ModelLayerError): pass
class NoCompatibleModelError(ModelLayerError): pass
