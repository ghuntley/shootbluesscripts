﻿from shootblues.common import log, showException

runningServices = {}

def get(serviceName):
    global runningServices
    
    result = runningServices.get(serviceName, None)
    if not result:
        result = sm.services.get(serviceName, None)
    
    return result

def wrapMethod(methodName, innerMethod):
    def wrapper(*args, **kwargs):
        result = None
        
        try:
            result = innerMethod(*args, **kwargs)
        except Exception, e:
            showException()
        
        return result
    
    wrapper.func_name = methodName
    return wrapper

def makeServiceThunk(serviceInstance):
    result = serviceInstance
    
    ne = getattr(serviceInstance, "__notifyevents__", [])
    for evt in ne:
        innerMethod = getattr(result, evt, None)
        if innerMethod:
            setattr(result, evt, wrapMethod(evt, innerMethod))
    
    return result

def forceStop(serviceName):
    global runningServices
    
    import stackless
    old_block_trap = stackless.getcurrent().block_trap
    stackless.getcurrent().block_trap = 1
    try:
        serviceInstance = runningServices.get(serviceName, None)
        if serviceInstance:
            del runningServices[serviceName]
            ne = getattr(serviceInstance, "__notifyevents__", [])
            for evt in ne:
                nl = sm.notify.setdefault(evt, list())
                if serviceInstance in nl:
                    nl.remove(serviceInstance)
    finally:
        stackless.getcurrent().block_trap = old_block_trap

def forceStart(serviceName, serviceType):
    global runningServices
    
    import stackless
    import service
    old_block_trap = stackless.getcurrent().block_trap
    stackless.getcurrent().block_trap = 1
    try:
        oldInstance = runningServices.get(serviceName, None)
        if oldInstance:
            forceStop(serviceName)
        
        result = serviceType()
        setattr(result, "state", service.SERVICE_RUNNING)
        result = makeServiceThunk(result)
        runningServices[serviceName] = result
        
        ne = getattr(result, "__notifyevents__", [])
        if len(ne):
            for evt in ne:
                if (not hasattr(result, evt)):
                    log("Missing event handler for %r on %r", evt, result)
                else:
                    nl = sm.notify.setdefault(evt, list())
                    nl.append(result)
        
        return result
    finally:
        stackless.getcurrent().block_trap = old_block_trap