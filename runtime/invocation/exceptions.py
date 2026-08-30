class InvocationError(Exception): pass
class AdapterNotFoundError(InvocationError): pass
class InvocationTimeoutError(InvocationError): pass
class InvocationUnavailableError(InvocationError): pass
class StreamUnsupportedError(InvocationError): pass
class StreamConnectionError(InvocationError): pass
