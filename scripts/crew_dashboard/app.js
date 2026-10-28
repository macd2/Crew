// GENERATED from ui/src/browser.tsx by ui/build.mjs. Do not edit by hand: change the source and run `node ui/build.mjs`.
"use strict";
(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/react/cjs/react.production.js
  var require_react_production = __commonJS({
    "node_modules/react/cjs/react.production.js"(exports) {
      "use strict";
      var REACT_ELEMENT_TYPE = Symbol.for("react.transitional.element");
      var REACT_PORTAL_TYPE = Symbol.for("react.portal");
      var REACT_FRAGMENT_TYPE = Symbol.for("react.fragment");
      var REACT_STRICT_MODE_TYPE = Symbol.for("react.strict_mode");
      var REACT_PROFILER_TYPE = Symbol.for("react.profiler");
      var REACT_CONSUMER_TYPE = Symbol.for("react.consumer");
      var REACT_CONTEXT_TYPE = Symbol.for("react.context");
      var REACT_FORWARD_REF_TYPE = Symbol.for("react.forward_ref");
      var REACT_SUSPENSE_TYPE = Symbol.for("react.suspense");
      var REACT_MEMO_TYPE = Symbol.for("react.memo");
      var REACT_LAZY_TYPE = Symbol.for("react.lazy");
      var REACT_ACTIVITY_TYPE = Symbol.for("react.activity");
      var MAYBE_ITERATOR_SYMBOL = Symbol.iterator;
      function getIteratorFn(maybeIterable) {
        if (null === maybeIterable || "object" !== typeof maybeIterable) return null;
        maybeIterable = MAYBE_ITERATOR_SYMBOL && maybeIterable[MAYBE_ITERATOR_SYMBOL] || maybeIterable["@@iterator"];
        return "function" === typeof maybeIterable ? maybeIterable : null;
      }
      var ReactNoopUpdateQueue = {
        isMounted: function() {
          return false;
        },
        enqueueForceUpdate: function() {
        },
        enqueueReplaceState: function() {
        },
        enqueueSetState: function() {
        }
      };
      var assign = Object.assign;
      var emptyObject = {};
      function Component(props, context, updater) {
        this.props = props;
        this.context = context;
        this.refs = emptyObject;
        this.updater = updater || ReactNoopUpdateQueue;
      }
      Component.prototype.isReactComponent = {};
      Component.prototype.setState = function(partialState, callback) {
        if ("object" !== typeof partialState && "function" !== typeof partialState && null != partialState)
          throw Error(
            "takes an object of state variables to update or a function which returns an object of state variables."
          );
        this.updater.enqueueSetState(this, partialState, callback, "setState");
      };
      Component.prototype.forceUpdate = function(callback) {
        this.updater.enqueueForceUpdate(this, callback, "forceUpdate");
      };
      function ComponentDummy() {
      }
      ComponentDummy.prototype = Component.prototype;
      function PureComponent(props, context, updater) {
        this.props = props;
        this.context = context;
        this.refs = emptyObject;
        this.updater = updater || ReactNoopUpdateQueue;
      }
      var pureComponentPrototype = PureComponent.prototype = new ComponentDummy();
      pureComponentPrototype.constructor = PureComponent;
      assign(pureComponentPrototype, Component.prototype);
      pureComponentPrototype.isPureReactComponent = true;
      var isArrayImpl = Array.isArray;
      function noop() {
      }
      var ReactSharedInternals = { H: null, A: null, T: null, S: null };
      var hasOwnProperty = Object.prototype.hasOwnProperty;
      function ReactElement(type, key, props) {
        var refProp = props.ref;
        return {
          $$typeof: REACT_ELEMENT_TYPE,
          type,
          key,
          ref: void 0 !== refProp ? refProp : null,
          props
        };
      }
      function cloneAndReplaceKey(oldElement, newKey) {
        return ReactElement(oldElement.type, newKey, oldElement.props);
      }
      function isValidElement(object) {
        return "object" === typeof object && null !== object && object.$$typeof === REACT_ELEMENT_TYPE;
      }
      function escape(key) {
        var escaperLookup = { "=": "=0", ":": "=2" };
        return "$" + key.replace(/[=:]/g, function(match) {
          return escaperLookup[match];
        });
      }
      var userProvidedKeyEscapeRegex = /\/+/g;
      function getElementKey(element, index) {
        return "object" === typeof element && null !== element && null != element.key ? escape("" + element.key) : index.toString(36);
      }
      function resolveThenable(thenable) {
        switch (thenable.status) {
          case "fulfilled":
            return thenable.value;
          case "rejected":
            throw thenable.reason;
          default:
            switch ("string" === typeof thenable.status ? thenable.then(noop, noop) : (thenable.status = "pending", thenable.then(
              function(fulfilledValue) {
                "pending" === thenable.status && (thenable.status = "fulfilled", thenable.value = fulfilledValue);
              },
              function(error) {
                "pending" === thenable.status && (thenable.status = "rejected", thenable.reason = error);
              }
            )), thenable.status) {
              case "fulfilled":
                return thenable.value;
              case "rejected":
                throw thenable.reason;
            }
        }
        throw thenable;
      }
      function mapIntoArray(children, array, escapedPrefix, nameSoFar, callback) {
        var type = typeof children;
        if ("undefined" === type || "boolean" === type) children = null;
        var invokeCallback = false;
        if (null === children) invokeCallback = true;
        else
          switch (type) {
            case "bigint":
            case "string":
            case "number":
              invokeCallback = true;
              break;
            case "object":
              switch (children.$$typeof) {
                case REACT_ELEMENT_TYPE:
                case REACT_PORTAL_TYPE:
                  invokeCallback = true;
                  break;
                case REACT_LAZY_TYPE:
                  return invokeCallback = children._init, mapIntoArray(
                    invokeCallback(children._payload),
                    array,
                    escapedPrefix,
                    nameSoFar,
                    callback
                  );
              }
          }
        if (invokeCallback)
          return callback = callback(children), invokeCallback = "" === nameSoFar ? "." + getElementKey(children, 0) : nameSoFar, isArrayImpl(callback) ? (escapedPrefix = "", null != invokeCallback && (escapedPrefix = invokeCallback.replace(userProvidedKeyEscapeRegex, "$&/") + "/"), mapIntoArray(callback, array, escapedPrefix, "", function(c) {
            return c;
          })) : null != callback && (isValidElement(callback) && (callback = cloneAndReplaceKey(
            callback,
            escapedPrefix + (null == callback.key || children && children.key === callback.key ? "" : ("" + callback.key).replace(
              userProvidedKeyEscapeRegex,
              "$&/"
            ) + "/") + invokeCallback
          )), array.push(callback)), 1;
        invokeCallback = 0;
        var nextNamePrefix = "" === nameSoFar ? "." : nameSoFar + ":";
        if (isArrayImpl(children))
          for (var i = 0; i < children.length; i++)
            nameSoFar = children[i], type = nextNamePrefix + getElementKey(nameSoFar, i), invokeCallback += mapIntoArray(
              nameSoFar,
              array,
              escapedPrefix,
              type,
              callback
            );
        else if (i = getIteratorFn(children), "function" === typeof i)
          for (children = i.call(children), i = 0; !(nameSoFar = children.next()).done; )
            nameSoFar = nameSoFar.value, type = nextNamePrefix + getElementKey(nameSoFar, i++), invokeCallback += mapIntoArray(
              nameSoFar,
              array,
              escapedPrefix,
              type,
              callback
            );
        else if ("object" === type) {
          if ("function" === typeof children.then)
            return mapIntoArray(
              resolveThenable(children),
              array,
              escapedPrefix,
              nameSoFar,
              callback
            );
          array = String(children);
          throw Error(
            "Objects are not valid as a React child (found: " + ("[object Object]" === array ? "object with keys {" + Object.keys(children).join(", ") + "}" : array) + "). If you meant to render a collection of children, use an array instead."
          );
        }
        return invokeCallback;
      }
      function mapChildren(children, func, context) {
        if (null == children) return children;
        var result = [], count = 0;
        mapIntoArray(children, result, "", "", function(child) {
          return func.call(context, child, count++);
        });
        return result;
      }
      function lazyInitializer(payload) {
        if (-1 === payload._status) {
          var ctor = payload._result;
          ctor = ctor();
          ctor.then(
            function(moduleObject) {
              if (0 === payload._status || -1 === payload._status)
                payload._status = 1, payload._result = moduleObject;
            },
            function(error) {
              if (0 === payload._status || -1 === payload._status)
                payload._status = 2, payload._result = error;
            }
          );
          -1 === payload._status && (payload._status = 0, payload._result = ctor);
        }
        if (1 === payload._status) return payload._result.default;
        throw payload._result;
      }
      var reportGlobalError = "function" === typeof reportError ? reportError : function(error) {
        if ("object" === typeof window && "function" === typeof window.ErrorEvent) {
          var event = new window.ErrorEvent("error", {
            bubbles: true,
            cancelable: true,
            message: "object" === typeof error && null !== error && "string" === typeof error.message ? String(error.message) : String(error),
            error
          });
          if (!window.dispatchEvent(event)) return;
        } else if ("object" === typeof process && "function" === typeof process.emit) {
          process.emit("uncaughtException", error);
          return;
        }
        console.error(error);
      };
      var Children = {
        map: mapChildren,
        forEach: function(children, forEachFunc, forEachContext) {
          mapChildren(
            children,
            function() {
              forEachFunc.apply(this, arguments);
            },
            forEachContext
          );
        },
        count: function(children) {
          var n = 0;
          mapChildren(children, function() {
            n++;
          });
          return n;
        },
        toArray: function(children) {
          return mapChildren(children, function(child) {
            return child;
          }) || [];
        },
        only: function(children) {
          if (!isValidElement(children))
            throw Error(
              "React.Children.only expected to receive a single React element child."
            );
          return children;
        }
      };
      exports.Activity = REACT_ACTIVITY_TYPE;
      exports.Children = Children;
      exports.Component = Component;
      exports.Fragment = REACT_FRAGMENT_TYPE;
      exports.Profiler = REACT_PROFILER_TYPE;
      exports.PureComponent = PureComponent;
      exports.StrictMode = REACT_STRICT_MODE_TYPE;
      exports.Suspense = REACT_SUSPENSE_TYPE;
      exports.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = ReactSharedInternals;
      exports.__COMPILER_RUNTIME = {
        __proto__: null,
        c: function(size) {
          return ReactSharedInternals.H.useMemoCache(size);
        }
      };
      exports.cache = function(fn) {
        return function() {
          return fn.apply(null, arguments);
        };
      };
      exports.cacheSignal = function() {
        return null;
      };
      exports.cloneElement = function(element, config, children) {
        if (null === element || void 0 === element)
          throw Error(
            "The argument must be a React element, but you passed " + element + "."
          );
        var props = assign({}, element.props), key = element.key;
        if (null != config)
          for (propName in void 0 !== config.key && (key = "" + config.key), config)
            !hasOwnProperty.call(config, propName) || "key" === propName || "__self" === propName || "__source" === propName || "ref" === propName && void 0 === config.ref || (props[propName] = config[propName]);
        var propName = arguments.length - 2;
        if (1 === propName) props.children = children;
        else if (1 < propName) {
          for (var childArray = Array(propName), i = 0; i < propName; i++)
            childArray[i] = arguments[i + 2];
          props.children = childArray;
        }
        return ReactElement(element.type, key, props);
      };
      exports.createContext = function(defaultValue) {
        defaultValue = {
          $$typeof: REACT_CONTEXT_TYPE,
          _currentValue: defaultValue,
          _currentValue2: defaultValue,
          _threadCount: 0,
          Provider: null,
          Consumer: null
        };
        defaultValue.Provider = defaultValue;
        defaultValue.Consumer = {
          $$typeof: REACT_CONSUMER_TYPE,
          _context: defaultValue
        };
        return defaultValue;
      };
      exports.createElement = function(type, config, children) {
        var propName, props = {}, key = null;
        if (null != config)
          for (propName in void 0 !== config.key && (key = "" + config.key), config)
            hasOwnProperty.call(config, propName) && "key" !== propName && "__self" !== propName && "__source" !== propName && (props[propName] = config[propName]);
        var childrenLength = arguments.length - 2;
        if (1 === childrenLength) props.children = children;
        else if (1 < childrenLength) {
          for (var childArray = Array(childrenLength), i = 0; i < childrenLength; i++)
            childArray[i] = arguments[i + 2];
          props.children = childArray;
        }
        if (type && type.defaultProps)
          for (propName in childrenLength = type.defaultProps, childrenLength)
            void 0 === props[propName] && (props[propName] = childrenLength[propName]);
        return ReactElement(type, key, props);
      };
      exports.createRef = function() {
        return { current: null };
      };
      exports.forwardRef = function(render) {
        return { $$typeof: REACT_FORWARD_REF_TYPE, render };
      };
      exports.isValidElement = isValidElement;
      exports.lazy = function(ctor) {
        return {
          $$typeof: REACT_LAZY_TYPE,
          _payload: { _status: -1, _result: ctor },
          _init: lazyInitializer
        };
      };
      exports.memo = function(type, compare) {
        return {
          $$typeof: REACT_MEMO_TYPE,
          type,
          compare: void 0 === compare ? null : compare
        };
      };
      exports.startTransition = function(scope) {
        var prevTransition = ReactSharedInternals.T, currentTransition = {};
        ReactSharedInternals.T = currentTransition;
        try {
          var returnValue = scope(), onStartTransitionFinish = ReactSharedInternals.S;
          null !== onStartTransitionFinish && onStartTransitionFinish(currentTransition, returnValue);
          "object" === typeof returnValue && null !== returnValue && "function" === typeof returnValue.then && returnValue.then(noop, reportGlobalError);
        } catch (error) {
          reportGlobalError(error);
        } finally {
          null !== prevTransition && null !== currentTransition.types && (prevTransition.types = currentTransition.types), ReactSharedInternals.T = prevTransition;
        }
      };
      exports.unstable_useCacheRefresh = function() {
        return ReactSharedInternals.H.useCacheRefresh();
      };
      exports.use = function(usable) {
        return ReactSharedInternals.H.use(usable);
      };
      exports.useActionState = function(action, initialState, permalink) {
        return ReactSharedInternals.H.useActionState(action, initialState, permalink);
      };
      exports.useCallback = function(callback, deps) {
        return ReactSharedInternals.H.useCallback(callback, deps);
      };
      exports.useContext = function(Context) {
        return ReactSharedInternals.H.useContext(Context);
      };
      exports.useDebugValue = function() {
      };
      exports.useDeferredValue = function(value, initialValue) {
        return ReactSharedInternals.H.useDeferredValue(value, initialValue);
      };
      exports.useEffect = function(create, deps) {
        return ReactSharedInternals.H.useEffect(create, deps);
      };
      exports.useEffectEvent = function(callback) {
        return ReactSharedInternals.H.useEffectEvent(callback);
      };
      exports.useId = function() {
        return ReactSharedInternals.H.useId();
      };
      exports.useImperativeHandle = function(ref, create, deps) {
        return ReactSharedInternals.H.useImperativeHandle(ref, create, deps);
      };
      exports.useInsertionEffect = function(create, deps) {
        return ReactSharedInternals.H.useInsertionEffect(create, deps);
      };
      exports.useLayoutEffect = function(create, deps) {
        return ReactSharedInternals.H.useLayoutEffect(create, deps);
      };
      exports.useMemo = function(create, deps) {
        return ReactSharedInternals.H.useMemo(create, deps);
      };
      exports.useOptimistic = function(passthrough, reducer) {
        return ReactSharedInternals.H.useOptimistic(passthrough, reducer);
      };
      exports.useReducer = function(reducer, initialArg, init) {
        return ReactSharedInternals.H.useReducer(reducer, initialArg, init);
      };
      exports.useRef = function(initialValue) {
        return ReactSharedInternals.H.useRef(initialValue);
      };
      exports.useState = function(initialState) {
        return ReactSharedInternals.H.useState(initialState);
      };
      exports.useSyncExternalStore = function(subscribe, getSnapshot, getServerSnapshot) {
        return ReactSharedInternals.H.useSyncExternalStore(
          subscribe,
          getSnapshot,
          getServerSnapshot
        );
      };
      exports.useTransition = function() {
        return ReactSharedInternals.H.useTransition();
      };
      exports.version = "19.2.7";
    }
  });

  // node_modules/react/index.js
  var require_react = __commonJS({
    "node_modules/react/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_production();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/scheduler/cjs/scheduler.production.js
  var require_scheduler_production = __commonJS({
    "node_modules/scheduler/cjs/scheduler.production.js"(exports) {
      "use strict";
      function push(heap, node) {
        var index = heap.length;
        heap.push(node);
        a: for (; 0 < index; ) {
          var parentIndex = index - 1 >>> 1, parent = heap[parentIndex];
          if (0 < compare(parent, node))
            heap[parentIndex] = node, heap[index] = parent, index = parentIndex;
          else break a;
        }
      }
      function peek(heap) {
        return 0 === heap.length ? null : heap[0];
      }
      function pop(heap) {
        if (0 === heap.length) return null;
        var first = heap[0], last = heap.pop();
        if (last !== first) {
          heap[0] = last;
          a: for (var index = 0, length = heap.length, halfLength = length >>> 1; index < halfLength; ) {
            var leftIndex = 2 * (index + 1) - 1, left = heap[leftIndex], rightIndex = leftIndex + 1, right = heap[rightIndex];
            if (0 > compare(left, last))
              rightIndex < length && 0 > compare(right, left) ? (heap[index] = right, heap[rightIndex] = last, index = rightIndex) : (heap[index] = left, heap[leftIndex] = last, index = leftIndex);
            else if (rightIndex < length && 0 > compare(right, last))
              heap[index] = right, heap[rightIndex] = last, index = rightIndex;
            else break a;
          }
        }
        return first;
      }
      function compare(a, b) {
        var diff = a.sortIndex - b.sortIndex;
        return 0 !== diff ? diff : a.id - b.id;
      }
      exports.unstable_now = void 0;
      if ("object" === typeof performance && "function" === typeof performance.now) {
        localPerformance = performance;
        exports.unstable_now = function() {
          return localPerformance.now();
        };
      } else {
        localDate = Date, initialTime = localDate.now();
        exports.unstable_now = function() {
          return localDate.now() - initialTime;
        };
      }
      var localPerformance;
      var localDate;
      var initialTime;
      var taskQueue = [];
      var timerQueue = [];
      var taskIdCounter = 1;
      var currentTask = null;
      var currentPriorityLevel = 3;
      var isPerformingWork = false;
      var isHostCallbackScheduled = false;
      var isHostTimeoutScheduled = false;
      var needsPaint = false;
      var localSetTimeout = "function" === typeof setTimeout ? setTimeout : null;
      var localClearTimeout = "function" === typeof clearTimeout ? clearTimeout : null;
      var localSetImmediate = "undefined" !== typeof setImmediate ? setImmediate : null;
      function advanceTimers(currentTime) {
        for (var timer = peek(timerQueue); null !== timer; ) {
          if (null === timer.callback) pop(timerQueue);
          else if (timer.startTime <= currentTime)
            pop(timerQueue), timer.sortIndex = timer.expirationTime, push(taskQueue, timer);
          else break;
          timer = peek(timerQueue);
        }
      }
      function handleTimeout(currentTime) {
        isHostTimeoutScheduled = false;
        advanceTimers(currentTime);
        if (!isHostCallbackScheduled)
          if (null !== peek(taskQueue))
            isHostCallbackScheduled = true, isMessageLoopRunning || (isMessageLoopRunning = true, schedulePerformWorkUntilDeadline());
          else {
            var firstTimer = peek(timerQueue);
            null !== firstTimer && requestHostTimeout(handleTimeout, firstTimer.startTime - currentTime);
          }
      }
      var isMessageLoopRunning = false;
      var taskTimeoutID = -1;
      var frameInterval = 5;
      var startTime = -1;
      function shouldYieldToHost() {
        return needsPaint ? true : exports.unstable_now() - startTime < frameInterval ? false : true;
      }
      function performWorkUntilDeadline() {
        needsPaint = false;
        if (isMessageLoopRunning) {
          var currentTime = exports.unstable_now();
          startTime = currentTime;
          var hasMoreWork = true;
          try {
            a: {
              isHostCallbackScheduled = false;
              isHostTimeoutScheduled && (isHostTimeoutScheduled = false, localClearTimeout(taskTimeoutID), taskTimeoutID = -1);
              isPerformingWork = true;
              var previousPriorityLevel = currentPriorityLevel;
              try {
                b: {
                  advanceTimers(currentTime);
                  for (currentTask = peek(taskQueue); null !== currentTask && !(currentTask.expirationTime > currentTime && shouldYieldToHost()); ) {
                    var callback = currentTask.callback;
                    if ("function" === typeof callback) {
                      currentTask.callback = null;
                      currentPriorityLevel = currentTask.priorityLevel;
                      var continuationCallback = callback(
                        currentTask.expirationTime <= currentTime
                      );
                      currentTime = exports.unstable_now();
                      if ("function" === typeof continuationCallback) {
                        currentTask.callback = continuationCallback;
                        advanceTimers(currentTime);
                        hasMoreWork = true;
                        break b;
                      }
                      currentTask === peek(taskQueue) && pop(taskQueue);
                      advanceTimers(currentTime);
                    } else pop(taskQueue);
                    currentTask = peek(taskQueue);
                  }
                  if (null !== currentTask) hasMoreWork = true;
                  else {
                    var firstTimer = peek(timerQueue);
                    null !== firstTimer && requestHostTimeout(
                      handleTimeout,
                      firstTimer.startTime - currentTime
                    );
                    hasMoreWork = false;
                  }
                }
                break a;
              } finally {
                currentTask = null, currentPriorityLevel = previousPriorityLevel, isPerformingWork = false;
              }
              hasMoreWork = void 0;
            }
          } finally {
            hasMoreWork ? schedulePerformWorkUntilDeadline() : isMessageLoopRunning = false;
          }
        }
      }
      var schedulePerformWorkUntilDeadline;
      if ("function" === typeof localSetImmediate)
        schedulePerformWorkUntilDeadline = function() {
          localSetImmediate(performWorkUntilDeadline);
        };
      else if ("undefined" !== typeof MessageChannel) {
        channel = new MessageChannel(), port = channel.port2;
        channel.port1.onmessage = performWorkUntilDeadline;
        schedulePerformWorkUntilDeadline = function() {
          port.postMessage(null);
        };
      } else
        schedulePerformWorkUntilDeadline = function() {
          localSetTimeout(performWorkUntilDeadline, 0);
        };
      var channel;
      var port;
      function requestHostTimeout(callback, ms) {
        taskTimeoutID = localSetTimeout(function() {
          callback(exports.unstable_now());
        }, ms);
      }
      exports.unstable_IdlePriority = 5;
      exports.unstable_ImmediatePriority = 1;
      exports.unstable_LowPriority = 4;
      exports.unstable_NormalPriority = 3;
      exports.unstable_Profiling = null;
      exports.unstable_UserBlockingPriority = 2;
      exports.unstable_cancelCallback = function(task) {
        task.callback = null;
      };
      exports.unstable_forceFrameRate = function(fps) {
        0 > fps || 125 < fps ? console.error(
          "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"
        ) : frameInterval = 0 < fps ? Math.floor(1e3 / fps) : 5;
      };
      exports.unstable_getCurrentPriorityLevel = function() {
        return currentPriorityLevel;
      };
      exports.unstable_next = function(eventHandler) {
        switch (currentPriorityLevel) {
          case 1:
          case 2:
          case 3:
            var priorityLevel = 3;
            break;
          default:
            priorityLevel = currentPriorityLevel;
        }
        var previousPriorityLevel = currentPriorityLevel;
        currentPriorityLevel = priorityLevel;
        try {
          return eventHandler();
        } finally {
          currentPriorityLevel = previousPriorityLevel;
        }
      };
      exports.unstable_requestPaint = function() {
        needsPaint = true;
      };
      exports.unstable_runWithPriority = function(priorityLevel, eventHandler) {
        switch (priorityLevel) {
          case 1:
          case 2:
          case 3:
          case 4:
          case 5:
            break;
          default:
            priorityLevel = 3;
        }
        var previousPriorityLevel = currentPriorityLevel;
        currentPriorityLevel = priorityLevel;
        try {
          return eventHandler();
        } finally {
          currentPriorityLevel = previousPriorityLevel;
        }
      };
      exports.unstable_scheduleCallback = function(priorityLevel, callback, options) {
        var currentTime = exports.unstable_now();
        "object" === typeof options && null !== options ? (options = options.delay, options = "number" === typeof options && 0 < options ? currentTime + options : currentTime) : options = currentTime;
        switch (priorityLevel) {
          case 1:
            var timeout = -1;
            break;
          case 2:
            timeout = 250;
            break;
          case 5:
            timeout = 1073741823;
            break;
          case 4:
            timeout = 1e4;
            break;
          default:
            timeout = 5e3;
        }
        timeout = options + timeout;
        priorityLevel = {
          id: taskIdCounter++,
          callback,
          priorityLevel,
          startTime: options,
          expirationTime: timeout,
          sortIndex: -1
        };
        options > currentTime ? (priorityLevel.sortIndex = options, push(timerQueue, priorityLevel), null === peek(taskQueue) && priorityLevel === peek(timerQueue) && (isHostTimeoutScheduled ? (localClearTimeout(taskTimeoutID), taskTimeoutID = -1) : isHostTimeoutScheduled = true, requestHostTimeout(handleTimeout, options - currentTime))) : (priorityLevel.sortIndex = timeout, push(taskQueue, priorityLevel), isHostCallbackScheduled || isPerformingWork || (isHostCallbackScheduled = true, isMessageLoopRunning || (isMessageLoopRunning = true, schedulePerformWorkUntilDeadline())));
        return priorityLevel;
      };
      exports.unstable_shouldYield = shouldYieldToHost;
      exports.unstable_wrapCallback = function(callback) {
        var parentPriorityLevel = currentPriorityLevel;
        return function() {
          var previousPriorityLevel = currentPriorityLevel;
          currentPriorityLevel = parentPriorityLevel;
          try {
            return callback.apply(this, arguments);
          } finally {
            currentPriorityLevel = previousPriorityLevel;
          }
        };
      };
    }
  });

  // node_modules/scheduler/index.js
  var require_scheduler = __commonJS({
    "node_modules/scheduler/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_scheduler_production();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/cjs/react-dom.production.js
  var require_react_dom_production = __commonJS({
    "node_modules/react-dom/cjs/react-dom.production.js"(exports) {
      "use strict";
      var React = require_react();
      function formatProdErrorMessage(code) {
        var url = "https://react.dev/errors/" + code;
        if (1 < arguments.length) {
          url += "?args[]=" + encodeURIComponent(arguments[1]);
          for (var i = 2; i < arguments.length; i++)
            url += "&args[]=" + encodeURIComponent(arguments[i]);
        }
        return "Minified React error #" + code + "; visit " + url + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
      }
      function noop() {
      }
      var Internals = {
        d: {
          f: noop,
          r: function() {
            throw Error(formatProdErrorMessage(522));
          },
          D: noop,
          C: noop,
          L: noop,
          m: noop,
          X: noop,
          S: noop,
          M: noop
        },
        p: 0,
        findDOMNode: null
      };
      var REACT_PORTAL_TYPE = Symbol.for("react.portal");
      function createPortal$1(children, containerInfo, implementation) {
        var key = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : null;
        return {
          $$typeof: REACT_PORTAL_TYPE,
          key: null == key ? null : "" + key,
          children,
          containerInfo,
          implementation
        };
      }
      var ReactSharedInternals = React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
      function getCrossOriginStringAs(as, input) {
        if ("font" === as) return "";
        if ("string" === typeof input)
          return "use-credentials" === input ? input : "";
      }
      exports.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = Internals;
      exports.createPortal = function(children, container) {
        var key = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : null;
        if (!container || 1 !== container.nodeType && 9 !== container.nodeType && 11 !== container.nodeType)
          throw Error(formatProdErrorMessage(299));
        return createPortal$1(children, container, null, key);
      };
      exports.flushSync = function(fn) {
        var previousTransition = ReactSharedInternals.T, previousUpdatePriority = Internals.p;
        try {
          if (ReactSharedInternals.T = null, Internals.p = 2, fn) return fn();
        } finally {
          ReactSharedInternals.T = previousTransition, Internals.p = previousUpdatePriority, Internals.d.f();
        }
      };
      exports.preconnect = function(href, options) {
        "string" === typeof href && (options ? (options = options.crossOrigin, options = "string" === typeof options ? "use-credentials" === options ? options : "" : void 0) : options = null, Internals.d.C(href, options));
      };
      exports.prefetchDNS = function(href) {
        "string" === typeof href && Internals.d.D(href);
      };
      exports.preinit = function(href, options) {
        if ("string" === typeof href && options && "string" === typeof options.as) {
          var as = options.as, crossOrigin = getCrossOriginStringAs(as, options.crossOrigin), integrity = "string" === typeof options.integrity ? options.integrity : void 0, fetchPriority = "string" === typeof options.fetchPriority ? options.fetchPriority : void 0;
          "style" === as ? Internals.d.S(
            href,
            "string" === typeof options.precedence ? options.precedence : void 0,
            {
              crossOrigin,
              integrity,
              fetchPriority
            }
          ) : "script" === as && Internals.d.X(href, {
            crossOrigin,
            integrity,
            fetchPriority,
            nonce: "string" === typeof options.nonce ? options.nonce : void 0
          });
        }
      };
      exports.preinitModule = function(href, options) {
        if ("string" === typeof href)
          if ("object" === typeof options && null !== options) {
            if (null == options.as || "script" === options.as) {
              var crossOrigin = getCrossOriginStringAs(
                options.as,
                options.crossOrigin
              );
              Internals.d.M(href, {
                crossOrigin,
                integrity: "string" === typeof options.integrity ? options.integrity : void 0,
                nonce: "string" === typeof options.nonce ? options.nonce : void 0
              });
            }
          } else null == options && Internals.d.M(href);
      };
      exports.preload = function(href, options) {
        if ("string" === typeof href && "object" === typeof options && null !== options && "string" === typeof options.as) {
          var as = options.as, crossOrigin = getCrossOriginStringAs(as, options.crossOrigin);
          Internals.d.L(href, as, {
            crossOrigin,
            integrity: "string" === typeof options.integrity ? options.integrity : void 0,
            nonce: "string" === typeof options.nonce ? options.nonce : void 0,
            type: "string" === typeof options.type ? options.type : void 0,
            fetchPriority: "string" === typeof options.fetchPriority ? options.fetchPriority : void 0,
            referrerPolicy: "string" === typeof options.referrerPolicy ? options.referrerPolicy : void 0,
            imageSrcSet: "string" === typeof options.imageSrcSet ? options.imageSrcSet : void 0,
            imageSizes: "string" === typeof options.imageSizes ? options.imageSizes : void 0,
            media: "string" === typeof options.media ? options.media : void 0
          });
        }
      };
      exports.preloadModule = function(href, options) {
        if ("string" === typeof href)
          if (options) {
            var crossOrigin = getCrossOriginStringAs(options.as, options.crossOrigin);
            Internals.d.m(href, {
              as: "string" === typeof options.as && "script" !== options.as ? options.as : void 0,
              crossOrigin,
              integrity: "string" === typeof options.integrity ? options.integrity : void 0
            });
          } else Internals.d.m(href);
      };
      exports.requestFormReset = function(form) {
        Internals.d.r(form);
      };
      exports.unstable_batchedUpdates = function(fn, a) {
        return fn(a);
      };
      exports.useFormState = function(action, initialState, permalink) {
        return ReactSharedInternals.H.useFormState(action, initialState, permalink);
      };
      exports.useFormStatus = function() {
        return ReactSharedInternals.H.useHostTransitionStatus();
      };
      exports.version = "19.2.7";
    }
  });

  // node_modules/react-dom/index.js
  var require_react_dom = __commonJS({
    "node_modules/react-dom/index.js"(exports, module) {
      "use strict";
      function checkDCE() {
        if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ === "undefined" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE !== "function") {
          return;
        }
        if (false) {
          throw new Error("^_^");
        }
        try {
          __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(checkDCE);
        } catch (err) {
          console.error(err);
        }
      }
      if (true) {
        checkDCE();
        module.exports = require_react_dom_production();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/cjs/react-dom-client.production.js
  var require_react_dom_client_production = __commonJS({
    "node_modules/react-dom/cjs/react-dom-client.production.js"(exports) {
      "use strict";
      var Scheduler = require_scheduler();
      var React = require_react();
      var ReactDOM = require_react_dom();
      function formatProdErrorMessage(code) {
        var url = "https://react.dev/errors/" + code;
        if (1 < arguments.length) {
          url += "?args[]=" + encodeURIComponent(arguments[1]);
          for (var i = 2; i < arguments.length; i++)
            url += "&args[]=" + encodeURIComponent(arguments[i]);
        }
        return "Minified React error #" + code + "; visit " + url + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
      }
      function isValidContainer(node) {
        return !(!node || 1 !== node.nodeType && 9 !== node.nodeType && 11 !== node.nodeType);
      }
      function getNearestMountedFiber(fiber) {
        var node = fiber, nearestMounted = fiber;
        if (fiber.alternate) for (; node.return; ) node = node.return;
        else {
          fiber = node;
          do
            node = fiber, 0 !== (node.flags & 4098) && (nearestMounted = node.return), fiber = node.return;
          while (fiber);
        }
        return 3 === node.tag ? nearestMounted : null;
      }
      function getSuspenseInstanceFromFiber(fiber) {
        if (13 === fiber.tag) {
          var suspenseState = fiber.memoizedState;
          null === suspenseState && (fiber = fiber.alternate, null !== fiber && (suspenseState = fiber.memoizedState));
          if (null !== suspenseState) return suspenseState.dehydrated;
        }
        return null;
      }
      function getActivityInstanceFromFiber(fiber) {
        if (31 === fiber.tag) {
          var activityState = fiber.memoizedState;
          null === activityState && (fiber = fiber.alternate, null !== fiber && (activityState = fiber.memoizedState));
          if (null !== activityState) return activityState.dehydrated;
        }
        return null;
      }
      function assertIsMounted(fiber) {
        if (getNearestMountedFiber(fiber) !== fiber)
          throw Error(formatProdErrorMessage(188));
      }
      function findCurrentFiberUsingSlowPath(fiber) {
        var alternate = fiber.alternate;
        if (!alternate) {
          alternate = getNearestMountedFiber(fiber);
          if (null === alternate) throw Error(formatProdErrorMessage(188));
          return alternate !== fiber ? null : fiber;
        }
        for (var a = fiber, b = alternate; ; ) {
          var parentA = a.return;
          if (null === parentA) break;
          var parentB = parentA.alternate;
          if (null === parentB) {
            b = parentA.return;
            if (null !== b) {
              a = b;
              continue;
            }
            break;
          }
          if (parentA.child === parentB.child) {
            for (parentB = parentA.child; parentB; ) {
              if (parentB === a) return assertIsMounted(parentA), fiber;
              if (parentB === b) return assertIsMounted(parentA), alternate;
              parentB = parentB.sibling;
            }
            throw Error(formatProdErrorMessage(188));
          }
          if (a.return !== b.return) a = parentA, b = parentB;
          else {
            for (var didFindChild = false, child$0 = parentA.child; child$0; ) {
              if (child$0 === a) {
                didFindChild = true;
                a = parentA;
                b = parentB;
                break;
              }
              if (child$0 === b) {
                didFindChild = true;
                b = parentA;
                a = parentB;
                break;
              }
              child$0 = child$0.sibling;
            }
            if (!didFindChild) {
              for (child$0 = parentB.child; child$0; ) {
                if (child$0 === a) {
                  didFindChild = true;
                  a = parentB;
                  b = parentA;
                  break;
                }
                if (child$0 === b) {
                  didFindChild = true;
                  b = parentB;
                  a = parentA;
                  break;
                }
                child$0 = child$0.sibling;
              }
              if (!didFindChild) throw Error(formatProdErrorMessage(189));
            }
          }
          if (a.alternate !== b) throw Error(formatProdErrorMessage(190));
        }
        if (3 !== a.tag) throw Error(formatProdErrorMessage(188));
        return a.stateNode.current === a ? fiber : alternate;
      }
      function findCurrentHostFiberImpl(node) {
        var tag = node.tag;
        if (5 === tag || 26 === tag || 27 === tag || 6 === tag) return node;
        for (node = node.child; null !== node; ) {
          tag = findCurrentHostFiberImpl(node);
          if (null !== tag) return tag;
          node = node.sibling;
        }
        return null;
      }
      var assign = Object.assign;
      var REACT_LEGACY_ELEMENT_TYPE = Symbol.for("react.element");
      var REACT_ELEMENT_TYPE = Symbol.for("react.transitional.element");
      var REACT_PORTAL_TYPE = Symbol.for("react.portal");
      var REACT_FRAGMENT_TYPE = Symbol.for("react.fragment");
      var REACT_STRICT_MODE_TYPE = Symbol.for("react.strict_mode");
      var REACT_PROFILER_TYPE = Symbol.for("react.profiler");
      var REACT_CONSUMER_TYPE = Symbol.for("react.consumer");
      var REACT_CONTEXT_TYPE = Symbol.for("react.context");
      var REACT_FORWARD_REF_TYPE = Symbol.for("react.forward_ref");
      var REACT_SUSPENSE_TYPE = Symbol.for("react.suspense");
      var REACT_SUSPENSE_LIST_TYPE = Symbol.for("react.suspense_list");
      var REACT_MEMO_TYPE = Symbol.for("react.memo");
      var REACT_LAZY_TYPE = Symbol.for("react.lazy");
      Symbol.for("react.scope");
      var REACT_ACTIVITY_TYPE = Symbol.for("react.activity");
      Symbol.for("react.legacy_hidden");
      Symbol.for("react.tracing_marker");
      var REACT_MEMO_CACHE_SENTINEL = Symbol.for("react.memo_cache_sentinel");
      Symbol.for("react.view_transition");
      var MAYBE_ITERATOR_SYMBOL = Symbol.iterator;
      function getIteratorFn(maybeIterable) {
        if (null === maybeIterable || "object" !== typeof maybeIterable) return null;
        maybeIterable = MAYBE_ITERATOR_SYMBOL && maybeIterable[MAYBE_ITERATOR_SYMBOL] || maybeIterable["@@iterator"];
        return "function" === typeof maybeIterable ? maybeIterable : null;
      }
      var REACT_CLIENT_REFERENCE = Symbol.for("react.client.reference");
      function getComponentNameFromType(type) {
        if (null == type) return null;
        if ("function" === typeof type)
          return type.$$typeof === REACT_CLIENT_REFERENCE ? null : type.displayName || type.name || null;
        if ("string" === typeof type) return type;
        switch (type) {
          case REACT_FRAGMENT_TYPE:
            return "Fragment";
          case REACT_PROFILER_TYPE:
            return "Profiler";
          case REACT_STRICT_MODE_TYPE:
            return "StrictMode";
          case REACT_SUSPENSE_TYPE:
            return "Suspense";
          case REACT_SUSPENSE_LIST_TYPE:
            return "SuspenseList";
          case REACT_ACTIVITY_TYPE:
            return "Activity";
        }
        if ("object" === typeof type)
          switch (type.$$typeof) {
            case REACT_PORTAL_TYPE:
              return "Portal";
            case REACT_CONTEXT_TYPE:
              return type.displayName || "Context";
            case REACT_CONSUMER_TYPE:
              return (type._context.displayName || "Context") + ".Consumer";
            case REACT_FORWARD_REF_TYPE:
              var innerType = type.render;
              type = type.displayName;
              type || (type = innerType.displayName || innerType.name || "", type = "" !== type ? "ForwardRef(" + type + ")" : "ForwardRef");
              return type;
            case REACT_MEMO_TYPE:
              return innerType = type.displayName || null, null !== innerType ? innerType : getComponentNameFromType(type.type) || "Memo";
            case REACT_LAZY_TYPE:
              innerType = type._payload;
              type = type._init;
              try {
                return getComponentNameFromType(type(innerType));
              } catch (x) {
              }
          }
        return null;
      }
      var isArrayImpl = Array.isArray;
      var ReactSharedInternals = React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
      var ReactDOMSharedInternals = ReactDOM.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
      var sharedNotPendingObject = {
        pending: false,
        data: null,
        method: null,
        action: null
      };
      var valueStack = [];
      var index = -1;
      function createCursor(defaultValue) {
        return { current: defaultValue };
      }
      function pop(cursor) {
        0 > index || (cursor.current = valueStack[index], valueStack[index] = null, index--);
      }
      function push(cursor, value) {
        index++;
        valueStack[index] = cursor.current;
        cursor.current = value;
      }
      var contextStackCursor = createCursor(null);
      var contextFiberStackCursor = createCursor(null);
      var rootInstanceStackCursor = createCursor(null);
      var hostTransitionProviderCursor = createCursor(null);
      function pushHostContainer(fiber, nextRootInstance) {
        push(rootInstanceStackCursor, nextRootInstance);
        push(contextFiberStackCursor, fiber);
        push(contextStackCursor, null);
        switch (nextRootInstance.nodeType) {
          case 9:
          case 11:
            fiber = (fiber = nextRootInstance.documentElement) ? (fiber = fiber.namespaceURI) ? getOwnHostContext(fiber) : 0 : 0;
            break;
          default:
            if (fiber = nextRootInstance.tagName, nextRootInstance = nextRootInstance.namespaceURI)
              nextRootInstance = getOwnHostContext(nextRootInstance), fiber = getChildHostContextProd(nextRootInstance, fiber);
            else
              switch (fiber) {
                case "svg":
                  fiber = 1;
                  break;
                case "math":
                  fiber = 2;
                  break;
                default:
                  fiber = 0;
              }
        }
        pop(contextStackCursor);
        push(contextStackCursor, fiber);
      }
      function popHostContainer() {
        pop(contextStackCursor);
        pop(contextFiberStackCursor);
        pop(rootInstanceStackCursor);
      }
      function pushHostContext(fiber) {
        null !== fiber.memoizedState && push(hostTransitionProviderCursor, fiber);
        var context = contextStackCursor.current;
        var JSCompiler_inline_result = getChildHostContextProd(context, fiber.type);
        context !== JSCompiler_inline_result && (push(contextFiberStackCursor, fiber), push(contextStackCursor, JSCompiler_inline_result));
      }
      function popHostContext(fiber) {
        contextFiberStackCursor.current === fiber && (pop(contextStackCursor), pop(contextFiberStackCursor));
        hostTransitionProviderCursor.current === fiber && (pop(hostTransitionProviderCursor), HostTransitionContext._currentValue = sharedNotPendingObject);
      }
      var prefix;
      var suffix;
      function describeBuiltInComponentFrame(name) {
        if (void 0 === prefix)
          try {
            throw Error();
          } catch (x) {
            var match = x.stack.trim().match(/\n( *(at )?)/);
            prefix = match && match[1] || "";
            suffix = -1 < x.stack.indexOf("\n    at") ? " (<anonymous>)" : -1 < x.stack.indexOf("@") ? "@unknown:0:0" : "";
          }
        return "\n" + prefix + name + suffix;
      }
      var reentry = false;
      function describeNativeComponentFrame(fn, construct) {
        if (!fn || reentry) return "";
        reentry = true;
        var previousPrepareStackTrace = Error.prepareStackTrace;
        Error.prepareStackTrace = void 0;
        try {
          var RunInRootFrame = {
            DetermineComponentFrameRoot: function() {
              try {
                if (construct) {
                  var Fake = function() {
                    throw Error();
                  };
                  Object.defineProperty(Fake.prototype, "props", {
                    set: function() {
                      throw Error();
                    }
                  });
                  if ("object" === typeof Reflect && Reflect.construct) {
                    try {
                      Reflect.construct(Fake, []);
                    } catch (x) {
                      var control = x;
                    }
                    Reflect.construct(fn, [], Fake);
                  } else {
                    try {
                      Fake.call();
                    } catch (x$1) {
                      control = x$1;
                    }
                    fn.call(Fake.prototype);
                  }
                } else {
                  try {
                    throw Error();
                  } catch (x$2) {
                    control = x$2;
                  }
                  (Fake = fn()) && "function" === typeof Fake.catch && Fake.catch(function() {
                  });
                }
              } catch (sample) {
                if (sample && control && "string" === typeof sample.stack)
                  return [sample.stack, control.stack];
              }
              return [null, null];
            }
          };
          RunInRootFrame.DetermineComponentFrameRoot.displayName = "DetermineComponentFrameRoot";
          var namePropDescriptor = Object.getOwnPropertyDescriptor(
            RunInRootFrame.DetermineComponentFrameRoot,
            "name"
          );
          namePropDescriptor && namePropDescriptor.configurable && Object.defineProperty(
            RunInRootFrame.DetermineComponentFrameRoot,
            "name",
            { value: "DetermineComponentFrameRoot" }
          );
          var _RunInRootFrame$Deter = RunInRootFrame.DetermineComponentFrameRoot(), sampleStack = _RunInRootFrame$Deter[0], controlStack = _RunInRootFrame$Deter[1];
          if (sampleStack && controlStack) {
            var sampleLines = sampleStack.split("\n"), controlLines = controlStack.split("\n");
            for (namePropDescriptor = RunInRootFrame = 0; RunInRootFrame < sampleLines.length && !sampleLines[RunInRootFrame].includes("DetermineComponentFrameRoot"); )
              RunInRootFrame++;
            for (; namePropDescriptor < controlLines.length && !controlLines[namePropDescriptor].includes(
              "DetermineComponentFrameRoot"
            ); )
              namePropDescriptor++;
            if (RunInRootFrame === sampleLines.length || namePropDescriptor === controlLines.length)
              for (RunInRootFrame = sampleLines.length - 1, namePropDescriptor = controlLines.length - 1; 1 <= RunInRootFrame && 0 <= namePropDescriptor && sampleLines[RunInRootFrame] !== controlLines[namePropDescriptor]; )
                namePropDescriptor--;
            for (; 1 <= RunInRootFrame && 0 <= namePropDescriptor; RunInRootFrame--, namePropDescriptor--)
              if (sampleLines[RunInRootFrame] !== controlLines[namePropDescriptor]) {
                if (1 !== RunInRootFrame || 1 !== namePropDescriptor) {
                  do
                    if (RunInRootFrame--, namePropDescriptor--, 0 > namePropDescriptor || sampleLines[RunInRootFrame] !== controlLines[namePropDescriptor]) {
                      var frame = "\n" + sampleLines[RunInRootFrame].replace(" at new ", " at ");
                      fn.displayName && frame.includes("<anonymous>") && (frame = frame.replace("<anonymous>", fn.displayName));
                      return frame;
                    }
                  while (1 <= RunInRootFrame && 0 <= namePropDescriptor);
                }
                break;
              }
          }
        } finally {
          reentry = false, Error.prepareStackTrace = previousPrepareStackTrace;
        }
        return (previousPrepareStackTrace = fn ? fn.displayName || fn.name : "") ? describeBuiltInComponentFrame(previousPrepareStackTrace) : "";
      }
      function describeFiber(fiber, childFiber) {
        switch (fiber.tag) {
          case 26:
          case 27:
          case 5:
            return describeBuiltInComponentFrame(fiber.type);
          case 16:
            return describeBuiltInComponentFrame("Lazy");
          case 13:
            return fiber.child !== childFiber && null !== childFiber ? describeBuiltInComponentFrame("Suspense Fallback") : describeBuiltInComponentFrame("Suspense");
          case 19:
            return describeBuiltInComponentFrame("SuspenseList");
          case 0:
          case 15:
            return describeNativeComponentFrame(fiber.type, false);
          case 11:
            return describeNativeComponentFrame(fiber.type.render, false);
          case 1:
            return describeNativeComponentFrame(fiber.type, true);
          case 31:
            return describeBuiltInComponentFrame("Activity");
          default:
            return "";
        }
      }
      function getStackByFiberInDevAndProd(workInProgress2) {
        try {
          var info = "", previous = null;
          do
            info += describeFiber(workInProgress2, previous), previous = workInProgress2, workInProgress2 = workInProgress2.return;
          while (workInProgress2);
          return info;
        } catch (x) {
          return "\nError generating stack: " + x.message + "\n" + x.stack;
        }
      }
      var hasOwnProperty = Object.prototype.hasOwnProperty;
      var scheduleCallback$3 = Scheduler.unstable_scheduleCallback;
      var cancelCallback$1 = Scheduler.unstable_cancelCallback;
      var shouldYield = Scheduler.unstable_shouldYield;
      var requestPaint = Scheduler.unstable_requestPaint;
      var now = Scheduler.unstable_now;
      var getCurrentPriorityLevel = Scheduler.unstable_getCurrentPriorityLevel;
      var ImmediatePriority = Scheduler.unstable_ImmediatePriority;
      var UserBlockingPriority = Scheduler.unstable_UserBlockingPriority;
      var NormalPriority$1 = Scheduler.unstable_NormalPriority;
      var LowPriority = Scheduler.unstable_LowPriority;
      var IdlePriority = Scheduler.unstable_IdlePriority;
      var log$1 = Scheduler.log;
      var unstable_setDisableYieldValue = Scheduler.unstable_setDisableYieldValue;
      var rendererID = null;
      var injectedHook = null;
      function setIsStrictModeForDevtools(newIsStrictMode) {
        "function" === typeof log$1 && unstable_setDisableYieldValue(newIsStrictMode);
        if (injectedHook && "function" === typeof injectedHook.setStrictMode)
          try {
            injectedHook.setStrictMode(rendererID, newIsStrictMode);
          } catch (err) {
          }
      }
      var clz32 = Math.clz32 ? Math.clz32 : clz32Fallback;
      var log = Math.log;
      var LN2 = Math.LN2;
      function clz32Fallback(x) {
        x >>>= 0;
        return 0 === x ? 32 : 31 - (log(x) / LN2 | 0) | 0;
      }
      var nextTransitionUpdateLane = 256;
      var nextTransitionDeferredLane = 262144;
      var nextRetryLane = 4194304;
      function getHighestPriorityLanes(lanes) {
        var pendingSyncLanes = lanes & 42;
        if (0 !== pendingSyncLanes) return pendingSyncLanes;
        switch (lanes & -lanes) {
          case 1:
            return 1;
          case 2:
            return 2;
          case 4:
            return 4;
          case 8:
            return 8;
          case 16:
            return 16;
          case 32:
            return 32;
          case 64:
            return 64;
          case 128:
            return 128;
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
            return lanes & 261888;
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return lanes & 3932160;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
            return lanes & 62914560;
          case 67108864:
            return 67108864;
          case 134217728:
            return 134217728;
          case 268435456:
            return 268435456;
          case 536870912:
            return 536870912;
          case 1073741824:
            return 0;
          default:
            return lanes;
        }
      }
      function getNextLanes(root2, wipLanes, rootHasPendingCommit) {
        var pendingLanes = root2.pendingLanes;
        if (0 === pendingLanes) return 0;
        var nextLanes = 0, suspendedLanes = root2.suspendedLanes, pingedLanes = root2.pingedLanes;
        root2 = root2.warmLanes;
        var nonIdlePendingLanes = pendingLanes & 134217727;
        0 !== nonIdlePendingLanes ? (pendingLanes = nonIdlePendingLanes & ~suspendedLanes, 0 !== pendingLanes ? nextLanes = getHighestPriorityLanes(pendingLanes) : (pingedLanes &= nonIdlePendingLanes, 0 !== pingedLanes ? nextLanes = getHighestPriorityLanes(pingedLanes) : rootHasPendingCommit || (rootHasPendingCommit = nonIdlePendingLanes & ~root2, 0 !== rootHasPendingCommit && (nextLanes = getHighestPriorityLanes(rootHasPendingCommit))))) : (nonIdlePendingLanes = pendingLanes & ~suspendedLanes, 0 !== nonIdlePendingLanes ? nextLanes = getHighestPriorityLanes(nonIdlePendingLanes) : 0 !== pingedLanes ? nextLanes = getHighestPriorityLanes(pingedLanes) : rootHasPendingCommit || (rootHasPendingCommit = pendingLanes & ~root2, 0 !== rootHasPendingCommit && (nextLanes = getHighestPriorityLanes(rootHasPendingCommit))));
        return 0 === nextLanes ? 0 : 0 !== wipLanes && wipLanes !== nextLanes && 0 === (wipLanes & suspendedLanes) && (suspendedLanes = nextLanes & -nextLanes, rootHasPendingCommit = wipLanes & -wipLanes, suspendedLanes >= rootHasPendingCommit || 32 === suspendedLanes && 0 !== (rootHasPendingCommit & 4194048)) ? wipLanes : nextLanes;
      }
      function checkIfRootIsPrerendering(root2, renderLanes2) {
        return 0 === (root2.pendingLanes & ~(root2.suspendedLanes & ~root2.pingedLanes) & renderLanes2);
      }
      function computeExpirationTime(lane, currentTime) {
        switch (lane) {
          case 1:
          case 2:
          case 4:
          case 8:
          case 64:
            return currentTime + 250;
          case 16:
          case 32:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return currentTime + 5e3;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
            return -1;
          case 67108864:
          case 134217728:
          case 268435456:
          case 536870912:
          case 1073741824:
            return -1;
          default:
            return -1;
        }
      }
      function claimNextRetryLane() {
        var lane = nextRetryLane;
        nextRetryLane <<= 1;
        0 === (nextRetryLane & 62914560) && (nextRetryLane = 4194304);
        return lane;
      }
      function createLaneMap(initial) {
        for (var laneMap = [], i = 0; 31 > i; i++) laneMap.push(initial);
        return laneMap;
      }
      function markRootUpdated$1(root2, updateLane) {
        root2.pendingLanes |= updateLane;
        268435456 !== updateLane && (root2.suspendedLanes = 0, root2.pingedLanes = 0, root2.warmLanes = 0);
      }
      function markRootFinished(root2, finishedLanes, remainingLanes, spawnedLane, updatedLanes, suspendedRetryLanes) {
        var previouslyPendingLanes = root2.pendingLanes;
        root2.pendingLanes = remainingLanes;
        root2.suspendedLanes = 0;
        root2.pingedLanes = 0;
        root2.warmLanes = 0;
        root2.expiredLanes &= remainingLanes;
        root2.entangledLanes &= remainingLanes;
        root2.errorRecoveryDisabledLanes &= remainingLanes;
        root2.shellSuspendCounter = 0;
        var entanglements = root2.entanglements, expirationTimes = root2.expirationTimes, hiddenUpdates = root2.hiddenUpdates;
        for (remainingLanes = previouslyPendingLanes & ~remainingLanes; 0 < remainingLanes; ) {
          var index$7 = 31 - clz32(remainingLanes), lane = 1 << index$7;
          entanglements[index$7] = 0;
          expirationTimes[index$7] = -1;
          var hiddenUpdatesForLane = hiddenUpdates[index$7];
          if (null !== hiddenUpdatesForLane)
            for (hiddenUpdates[index$7] = null, index$7 = 0; index$7 < hiddenUpdatesForLane.length; index$7++) {
              var update = hiddenUpdatesForLane[index$7];
              null !== update && (update.lane &= -536870913);
            }
          remainingLanes &= ~lane;
        }
        0 !== spawnedLane && markSpawnedDeferredLane(root2, spawnedLane, 0);
        0 !== suspendedRetryLanes && 0 === updatedLanes && 0 !== root2.tag && (root2.suspendedLanes |= suspendedRetryLanes & ~(previouslyPendingLanes & ~finishedLanes));
      }
      function markSpawnedDeferredLane(root2, spawnedLane, entangledLanes) {
        root2.pendingLanes |= spawnedLane;
        root2.suspendedLanes &= ~spawnedLane;
        var spawnedLaneIndex = 31 - clz32(spawnedLane);
        root2.entangledLanes |= spawnedLane;
        root2.entanglements[spawnedLaneIndex] = root2.entanglements[spawnedLaneIndex] | 1073741824 | entangledLanes & 261930;
      }
      function markRootEntangled(root2, entangledLanes) {
        var rootEntangledLanes = root2.entangledLanes |= entangledLanes;
        for (root2 = root2.entanglements; rootEntangledLanes; ) {
          var index$8 = 31 - clz32(rootEntangledLanes), lane = 1 << index$8;
          lane & entangledLanes | root2[index$8] & entangledLanes && (root2[index$8] |= entangledLanes);
          rootEntangledLanes &= ~lane;
        }
      }
      function getBumpedLaneForHydration(root2, renderLanes2) {
        var renderLane = renderLanes2 & -renderLanes2;
        renderLane = 0 !== (renderLane & 42) ? 1 : getBumpedLaneForHydrationByLane(renderLane);
        return 0 !== (renderLane & (root2.suspendedLanes | renderLanes2)) ? 0 : renderLane;
      }
      function getBumpedLaneForHydrationByLane(lane) {
        switch (lane) {
          case 2:
            lane = 1;
            break;
          case 8:
            lane = 4;
            break;
          case 32:
            lane = 16;
            break;
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
            lane = 128;
            break;
          case 268435456:
            lane = 134217728;
            break;
          default:
            lane = 0;
        }
        return lane;
      }
      function lanesToEventPriority(lanes) {
        lanes &= -lanes;
        return 2 < lanes ? 8 < lanes ? 0 !== (lanes & 134217727) ? 32 : 268435456 : 8 : 2;
      }
      function resolveUpdatePriority() {
        var updatePriority = ReactDOMSharedInternals.p;
        if (0 !== updatePriority) return updatePriority;
        updatePriority = window.event;
        return void 0 === updatePriority ? 32 : getEventPriority(updatePriority.type);
      }
      function runWithPriority(priority, fn) {
        var previousPriority = ReactDOMSharedInternals.p;
        try {
          return ReactDOMSharedInternals.p = priority, fn();
        } finally {
          ReactDOMSharedInternals.p = previousPriority;
        }
      }
      var randomKey = Math.random().toString(36).slice(2);
      var internalInstanceKey = "__reactFiber$" + randomKey;
      var internalPropsKey = "__reactProps$" + randomKey;
      var internalContainerInstanceKey = "__reactContainer$" + randomKey;
      var internalEventHandlersKey = "__reactEvents$" + randomKey;
      var internalEventHandlerListenersKey = "__reactListeners$" + randomKey;
      var internalEventHandlesSetKey = "__reactHandles$" + randomKey;
      var internalRootNodeResourcesKey = "__reactResources$" + randomKey;
      var internalHoistableMarker = "__reactMarker$" + randomKey;
      function detachDeletedInstance(node) {
        delete node[internalInstanceKey];
        delete node[internalPropsKey];
        delete node[internalEventHandlersKey];
        delete node[internalEventHandlerListenersKey];
        delete node[internalEventHandlesSetKey];
      }
      function getClosestInstanceFromNode(targetNode) {
        var targetInst = targetNode[internalInstanceKey];
        if (targetInst) return targetInst;
        for (var parentNode = targetNode.parentNode; parentNode; ) {
          if (targetInst = parentNode[internalContainerInstanceKey] || parentNode[internalInstanceKey]) {
            parentNode = targetInst.alternate;
            if (null !== targetInst.child || null !== parentNode && null !== parentNode.child)
              for (targetNode = getParentHydrationBoundary(targetNode); null !== targetNode; ) {
                if (parentNode = targetNode[internalInstanceKey]) return parentNode;
                targetNode = getParentHydrationBoundary(targetNode);
              }
            return targetInst;
          }
          targetNode = parentNode;
          parentNode = targetNode.parentNode;
        }
        return null;
      }
      function getInstanceFromNode(node) {
        if (node = node[internalInstanceKey] || node[internalContainerInstanceKey]) {
          var tag = node.tag;
          if (5 === tag || 6 === tag || 13 === tag || 31 === tag || 26 === tag || 27 === tag || 3 === tag)
            return node;
        }
        return null;
      }
      function getNodeFromInstance(inst) {
        var tag = inst.tag;
        if (5 === tag || 26 === tag || 27 === tag || 6 === tag) return inst.stateNode;
        throw Error(formatProdErrorMessage(33));
      }
      function getResourcesFromRoot(root2) {
        var resources = root2[internalRootNodeResourcesKey];
        resources || (resources = root2[internalRootNodeResourcesKey] = { hoistableStyles: /* @__PURE__ */ new Map(), hoistableScripts: /* @__PURE__ */ new Map() });
        return resources;
      }
      function markNodeAsHoistable(node) {
        node[internalHoistableMarker] = true;
      }
      var allNativeEvents = /* @__PURE__ */ new Set();
      var registrationNameDependencies = {};
      function registerTwoPhaseEvent(registrationName, dependencies) {
        registerDirectEvent(registrationName, dependencies);
        registerDirectEvent(registrationName + "Capture", dependencies);
      }
      function registerDirectEvent(registrationName, dependencies) {
        registrationNameDependencies[registrationName] = dependencies;
        for (registrationName = 0; registrationName < dependencies.length; registrationName++)
          allNativeEvents.add(dependencies[registrationName]);
      }
      var VALID_ATTRIBUTE_NAME_REGEX = RegExp(
        "^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$"
      );
      var illegalAttributeNameCache = {};
      var validatedAttributeNameCache = {};
      function isAttributeNameSafe(attributeName) {
        if (hasOwnProperty.call(validatedAttributeNameCache, attributeName))
          return true;
        if (hasOwnProperty.call(illegalAttributeNameCache, attributeName)) return false;
        if (VALID_ATTRIBUTE_NAME_REGEX.test(attributeName))
          return validatedAttributeNameCache[attributeName] = true;
        illegalAttributeNameCache[attributeName] = true;
        return false;
      }
      function setValueForAttribute(node, name, value) {
        if (isAttributeNameSafe(name))
          if (null === value) node.removeAttribute(name);
          else {
            switch (typeof value) {
              case "undefined":
              case "function":
              case "symbol":
                node.removeAttribute(name);
                return;
              case "boolean":
                var prefix$10 = name.toLowerCase().slice(0, 5);
                if ("data-" !== prefix$10 && "aria-" !== prefix$10) {
                  node.removeAttribute(name);
                  return;
                }
            }
            node.setAttribute(name, "" + value);
          }
      }
      function setValueForKnownAttribute(node, name, value) {
        if (null === value) node.removeAttribute(name);
        else {
          switch (typeof value) {
            case "undefined":
            case "function":
            case "symbol":
            case "boolean":
              node.removeAttribute(name);
              return;
          }
          node.setAttribute(name, "" + value);
        }
      }
      function setValueForNamespacedAttribute(node, namespace, name, value) {
        if (null === value) node.removeAttribute(name);
        else {
          switch (typeof value) {
            case "undefined":
            case "function":
            case "symbol":
            case "boolean":
              node.removeAttribute(name);
              return;
          }
          node.setAttributeNS(namespace, name, "" + value);
        }
      }
      function getToStringValue(value) {
        switch (typeof value) {
          case "bigint":
          case "boolean":
          case "number":
          case "string":
          case "undefined":
            return value;
          case "object":
            return value;
          default:
            return "";
        }
      }
      function isCheckable(elem) {
        var type = elem.type;
        return (elem = elem.nodeName) && "input" === elem.toLowerCase() && ("checkbox" === type || "radio" === type);
      }
      function trackValueOnNode(node, valueField, currentValue) {
        var descriptor = Object.getOwnPropertyDescriptor(
          node.constructor.prototype,
          valueField
        );
        if (!node.hasOwnProperty(valueField) && "undefined" !== typeof descriptor && "function" === typeof descriptor.get && "function" === typeof descriptor.set) {
          var get = descriptor.get, set = descriptor.set;
          Object.defineProperty(node, valueField, {
            configurable: true,
            get: function() {
              return get.call(this);
            },
            set: function(value) {
              currentValue = "" + value;
              set.call(this, value);
            }
          });
          Object.defineProperty(node, valueField, {
            enumerable: descriptor.enumerable
          });
          return {
            getValue: function() {
              return currentValue;
            },
            setValue: function(value) {
              currentValue = "" + value;
            },
            stopTracking: function() {
              node._valueTracker = null;
              delete node[valueField];
            }
          };
        }
      }
      function track(node) {
        if (!node._valueTracker) {
          var valueField = isCheckable(node) ? "checked" : "value";
          node._valueTracker = trackValueOnNode(
            node,
            valueField,
            "" + node[valueField]
          );
        }
      }
      function updateValueIfChanged(node) {
        if (!node) return false;
        var tracker = node._valueTracker;
        if (!tracker) return true;
        var lastValue = tracker.getValue();
        var value = "";
        node && (value = isCheckable(node) ? node.checked ? "true" : "false" : node.value);
        node = value;
        return node !== lastValue ? (tracker.setValue(node), true) : false;
      }
      function getActiveElement(doc) {
        doc = doc || ("undefined" !== typeof document ? document : void 0);
        if ("undefined" === typeof doc) return null;
        try {
          return doc.activeElement || doc.body;
        } catch (e) {
          return doc.body;
        }
      }
      var escapeSelectorAttributeValueInsideDoubleQuotesRegex = /[\n"\\]/g;
      function escapeSelectorAttributeValueInsideDoubleQuotes(value) {
        return value.replace(
          escapeSelectorAttributeValueInsideDoubleQuotesRegex,
          function(ch) {
            return "\\" + ch.charCodeAt(0).toString(16) + " ";
          }
        );
      }
      function updateInput(element, value, defaultValue, lastDefaultValue, checked, defaultChecked, type, name) {
        element.name = "";
        null != type && "function" !== typeof type && "symbol" !== typeof type && "boolean" !== typeof type ? element.type = type : element.removeAttribute("type");
        if (null != value)
          if ("number" === type) {
            if (0 === value && "" === element.value || element.value != value)
              element.value = "" + getToStringValue(value);
          } else
            element.value !== "" + getToStringValue(value) && (element.value = "" + getToStringValue(value));
        else
          "submit" !== type && "reset" !== type || element.removeAttribute("value");
        null != value ? setDefaultValue(element, type, getToStringValue(value)) : null != defaultValue ? setDefaultValue(element, type, getToStringValue(defaultValue)) : null != lastDefaultValue && element.removeAttribute("value");
        null == checked && null != defaultChecked && (element.defaultChecked = !!defaultChecked);
        null != checked && (element.checked = checked && "function" !== typeof checked && "symbol" !== typeof checked);
        null != name && "function" !== typeof name && "symbol" !== typeof name && "boolean" !== typeof name ? element.name = "" + getToStringValue(name) : element.removeAttribute("name");
      }
      function initInput(element, value, defaultValue, checked, defaultChecked, type, name, isHydrating2) {
        null != type && "function" !== typeof type && "symbol" !== typeof type && "boolean" !== typeof type && (element.type = type);
        if (null != value || null != defaultValue) {
          if (!("submit" !== type && "reset" !== type || void 0 !== value && null !== value)) {
            track(element);
            return;
          }
          defaultValue = null != defaultValue ? "" + getToStringValue(defaultValue) : "";
          value = null != value ? "" + getToStringValue(value) : defaultValue;
          isHydrating2 || value === element.value || (element.value = value);
          element.defaultValue = value;
        }
        checked = null != checked ? checked : defaultChecked;
        checked = "function" !== typeof checked && "symbol" !== typeof checked && !!checked;
        element.checked = isHydrating2 ? element.checked : !!checked;
        element.defaultChecked = !!checked;
        null != name && "function" !== typeof name && "symbol" !== typeof name && "boolean" !== typeof name && (element.name = name);
        track(element);
      }
      function setDefaultValue(node, type, value) {
        "number" === type && getActiveElement(node.ownerDocument) === node || node.defaultValue === "" + value || (node.defaultValue = "" + value);
      }
      function updateOptions(node, multiple, propValue, setDefaultSelected) {
        node = node.options;
        if (multiple) {
          multiple = {};
          for (var i = 0; i < propValue.length; i++)
            multiple["$" + propValue[i]] = true;
          for (propValue = 0; propValue < node.length; propValue++)
            i = multiple.hasOwnProperty("$" + node[propValue].value), node[propValue].selected !== i && (node[propValue].selected = i), i && setDefaultSelected && (node[propValue].defaultSelected = true);
        } else {
          propValue = "" + getToStringValue(propValue);
          multiple = null;
          for (i = 0; i < node.length; i++) {
            if (node[i].value === propValue) {
              node[i].selected = true;
              setDefaultSelected && (node[i].defaultSelected = true);
              return;
            }
            null !== multiple || node[i].disabled || (multiple = node[i]);
          }
          null !== multiple && (multiple.selected = true);
        }
      }
      function updateTextarea(element, value, defaultValue) {
        if (null != value && (value = "" + getToStringValue(value), value !== element.value && (element.value = value), null == defaultValue)) {
          element.defaultValue !== value && (element.defaultValue = value);
          return;
        }
        element.defaultValue = null != defaultValue ? "" + getToStringValue(defaultValue) : "";
      }
      function initTextarea(element, value, defaultValue, children) {
        if (null == value) {
          if (null != children) {
            if (null != defaultValue) throw Error(formatProdErrorMessage(92));
            if (isArrayImpl(children)) {
              if (1 < children.length) throw Error(formatProdErrorMessage(93));
              children = children[0];
            }
            defaultValue = children;
          }
          null == defaultValue && (defaultValue = "");
          value = defaultValue;
        }
        defaultValue = getToStringValue(value);
        element.defaultValue = defaultValue;
        children = element.textContent;
        children === defaultValue && "" !== children && null !== children && (element.value = children);
        track(element);
      }
      function setTextContent(node, text) {
        if (text) {
          var firstChild = node.firstChild;
          if (firstChild && firstChild === node.lastChild && 3 === firstChild.nodeType) {
            firstChild.nodeValue = text;
            return;
          }
        }
        node.textContent = text;
      }
      var unitlessNumbers = new Set(
        "animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp".split(
          " "
        )
      );
      function setValueForStyle(style2, styleName, value) {
        var isCustomProperty = 0 === styleName.indexOf("--");
        null == value || "boolean" === typeof value || "" === value ? isCustomProperty ? style2.setProperty(styleName, "") : "float" === styleName ? style2.cssFloat = "" : style2[styleName] = "" : isCustomProperty ? style2.setProperty(styleName, value) : "number" !== typeof value || 0 === value || unitlessNumbers.has(styleName) ? "float" === styleName ? style2.cssFloat = value : style2[styleName] = ("" + value).trim() : style2[styleName] = value + "px";
      }
      function setValueForStyles(node, styles, prevStyles) {
        if (null != styles && "object" !== typeof styles)
          throw Error(formatProdErrorMessage(62));
        node = node.style;
        if (null != prevStyles) {
          for (var styleName in prevStyles)
            !prevStyles.hasOwnProperty(styleName) || null != styles && styles.hasOwnProperty(styleName) || (0 === styleName.indexOf("--") ? node.setProperty(styleName, "") : "float" === styleName ? node.cssFloat = "" : node[styleName] = "");
          for (var styleName$16 in styles)
            styleName = styles[styleName$16], styles.hasOwnProperty(styleName$16) && prevStyles[styleName$16] !== styleName && setValueForStyle(node, styleName$16, styleName);
        } else
          for (var styleName$17 in styles)
            styles.hasOwnProperty(styleName$17) && setValueForStyle(node, styleName$17, styles[styleName$17]);
      }
      function isCustomElement(tagName) {
        if (-1 === tagName.indexOf("-")) return false;
        switch (tagName) {
          case "annotation-xml":
          case "color-profile":
          case "font-face":
          case "font-face-src":
          case "font-face-uri":
          case "font-face-format":
          case "font-face-name":
          case "missing-glyph":
            return false;
          default:
            return true;
        }
      }
      var aliases = /* @__PURE__ */ new Map([
        ["acceptCharset", "accept-charset"],
        ["htmlFor", "for"],
        ["httpEquiv", "http-equiv"],
        ["crossOrigin", "crossorigin"],
        ["accentHeight", "accent-height"],
        ["alignmentBaseline", "alignment-baseline"],
        ["arabicForm", "arabic-form"],
        ["baselineShift", "baseline-shift"],
        ["capHeight", "cap-height"],
        ["clipPath", "clip-path"],
        ["clipRule", "clip-rule"],
        ["colorInterpolation", "color-interpolation"],
        ["colorInterpolationFilters", "color-interpolation-filters"],
        ["colorProfile", "color-profile"],
        ["colorRendering", "color-rendering"],
        ["dominantBaseline", "dominant-baseline"],
        ["enableBackground", "enable-background"],
        ["fillOpacity", "fill-opacity"],
        ["fillRule", "fill-rule"],
        ["floodColor", "flood-color"],
        ["floodOpacity", "flood-opacity"],
        ["fontFamily", "font-family"],
        ["fontSize", "font-size"],
        ["fontSizeAdjust", "font-size-adjust"],
        ["fontStretch", "font-stretch"],
        ["fontStyle", "font-style"],
        ["fontVariant", "font-variant"],
        ["fontWeight", "font-weight"],
        ["glyphName", "glyph-name"],
        ["glyphOrientationHorizontal", "glyph-orientation-horizontal"],
        ["glyphOrientationVertical", "glyph-orientation-vertical"],
        ["horizAdvX", "horiz-adv-x"],
        ["horizOriginX", "horiz-origin-x"],
        ["imageRendering", "image-rendering"],
        ["letterSpacing", "letter-spacing"],
        ["lightingColor", "lighting-color"],
        ["markerEnd", "marker-end"],
        ["markerMid", "marker-mid"],
        ["markerStart", "marker-start"],
        ["overlinePosition", "overline-position"],
        ["overlineThickness", "overline-thickness"],
        ["paintOrder", "paint-order"],
        ["panose-1", "panose-1"],
        ["pointerEvents", "pointer-events"],
        ["renderingIntent", "rendering-intent"],
        ["shapeRendering", "shape-rendering"],
        ["stopColor", "stop-color"],
        ["stopOpacity", "stop-opacity"],
        ["strikethroughPosition", "strikethrough-position"],
        ["strikethroughThickness", "strikethrough-thickness"],
        ["strokeDasharray", "stroke-dasharray"],
        ["strokeDashoffset", "stroke-dashoffset"],
        ["strokeLinecap", "stroke-linecap"],
        ["strokeLinejoin", "stroke-linejoin"],
        ["strokeMiterlimit", "stroke-miterlimit"],
        ["strokeOpacity", "stroke-opacity"],
        ["strokeWidth", "stroke-width"],
        ["textAnchor", "text-anchor"],
        ["textDecoration", "text-decoration"],
        ["textRendering", "text-rendering"],
        ["transformOrigin", "transform-origin"],
        ["underlinePosition", "underline-position"],
        ["underlineThickness", "underline-thickness"],
        ["unicodeBidi", "unicode-bidi"],
        ["unicodeRange", "unicode-range"],
        ["unitsPerEm", "units-per-em"],
        ["vAlphabetic", "v-alphabetic"],
        ["vHanging", "v-hanging"],
        ["vIdeographic", "v-ideographic"],
        ["vMathematical", "v-mathematical"],
        ["vectorEffect", "vector-effect"],
        ["vertAdvY", "vert-adv-y"],
        ["vertOriginX", "vert-origin-x"],
        ["vertOriginY", "vert-origin-y"],
        ["wordSpacing", "word-spacing"],
        ["writingMode", "writing-mode"],
        ["xmlnsXlink", "xmlns:xlink"],
        ["xHeight", "x-height"]
      ]);
      var isJavaScriptProtocol = /^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;
      function sanitizeURL(url) {
        return isJavaScriptProtocol.test("" + url) ? "javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')" : url;
      }
      function noop$1() {
      }
      var currentReplayingEvent = null;
      function getEventTarget(nativeEvent) {
        nativeEvent = nativeEvent.target || nativeEvent.srcElement || window;
        nativeEvent.correspondingUseElement && (nativeEvent = nativeEvent.correspondingUseElement);
        return 3 === nativeEvent.nodeType ? nativeEvent.parentNode : nativeEvent;
      }
      var restoreTarget = null;
      var restoreQueue = null;
      function restoreStateOfTarget(target) {
        var internalInstance = getInstanceFromNode(target);
        if (internalInstance && (target = internalInstance.stateNode)) {
          var props = target[internalPropsKey] || null;
          a: switch (target = internalInstance.stateNode, internalInstance.type) {
            case "input":
              updateInput(
                target,
                props.value,
                props.defaultValue,
                props.defaultValue,
                props.checked,
                props.defaultChecked,
                props.type,
                props.name
              );
              internalInstance = props.name;
              if ("radio" === props.type && null != internalInstance) {
                for (props = target; props.parentNode; ) props = props.parentNode;
                props = props.querySelectorAll(
                  'input[name="' + escapeSelectorAttributeValueInsideDoubleQuotes(
                    "" + internalInstance
                  ) + '"][type="radio"]'
                );
                for (internalInstance = 0; internalInstance < props.length; internalInstance++) {
                  var otherNode = props[internalInstance];
                  if (otherNode !== target && otherNode.form === target.form) {
                    var otherProps = otherNode[internalPropsKey] || null;
                    if (!otherProps) throw Error(formatProdErrorMessage(90));
                    updateInput(
                      otherNode,
                      otherProps.value,
                      otherProps.defaultValue,
                      otherProps.defaultValue,
                      otherProps.checked,
                      otherProps.defaultChecked,
                      otherProps.type,
                      otherProps.name
                    );
                  }
                }
                for (internalInstance = 0; internalInstance < props.length; internalInstance++)
                  otherNode = props[internalInstance], otherNode.form === target.form && updateValueIfChanged(otherNode);
              }
              break a;
            case "textarea":
              updateTextarea(target, props.value, props.defaultValue);
              break a;
            case "select":
              internalInstance = props.value, null != internalInstance && updateOptions(target, !!props.multiple, internalInstance, false);
          }
        }
      }
      var isInsideEventHandler = false;
      function batchedUpdates$1(fn, a, b) {
        if (isInsideEventHandler) return fn(a, b);
        isInsideEventHandler = true;
        try {
          var JSCompiler_inline_result = fn(a);
          return JSCompiler_inline_result;
        } finally {
          if (isInsideEventHandler = false, null !== restoreTarget || null !== restoreQueue) {
            if (flushSyncWork$1(), restoreTarget && (a = restoreTarget, fn = restoreQueue, restoreQueue = restoreTarget = null, restoreStateOfTarget(a), fn))
              for (a = 0; a < fn.length; a++) restoreStateOfTarget(fn[a]);
          }
        }
      }
      function getListener(inst, registrationName) {
        var stateNode = inst.stateNode;
        if (null === stateNode) return null;
        var props = stateNode[internalPropsKey] || null;
        if (null === props) return null;
        stateNode = props[registrationName];
        a: switch (registrationName) {
          case "onClick":
          case "onClickCapture":
          case "onDoubleClick":
          case "onDoubleClickCapture":
          case "onMouseDown":
          case "onMouseDownCapture":
          case "onMouseMove":
          case "onMouseMoveCapture":
          case "onMouseUp":
          case "onMouseUpCapture":
          case "onMouseEnter":
            (props = !props.disabled) || (inst = inst.type, props = !("button" === inst || "input" === inst || "select" === inst || "textarea" === inst));
            inst = !props;
            break a;
          default:
            inst = false;
        }
        if (inst) return null;
        if (stateNode && "function" !== typeof stateNode)
          throw Error(
            formatProdErrorMessage(231, registrationName, typeof stateNode)
          );
        return stateNode;
      }
      var canUseDOM = !("undefined" === typeof window || "undefined" === typeof window.document || "undefined" === typeof window.document.createElement);
      var passiveBrowserEventsSupported = false;
      if (canUseDOM)
        try {
          options = {};
          Object.defineProperty(options, "passive", {
            get: function() {
              passiveBrowserEventsSupported = true;
            }
          });
          window.addEventListener("test", options, options);
          window.removeEventListener("test", options, options);
        } catch (e) {
          passiveBrowserEventsSupported = false;
        }
      var options;
      var root = null;
      var startText = null;
      var fallbackText = null;
      function getData() {
        if (fallbackText) return fallbackText;
        var start, startValue = startText, startLength = startValue.length, end, endValue = "value" in root ? root.value : root.textContent, endLength = endValue.length;
        for (start = 0; start < startLength && startValue[start] === endValue[start]; start++) ;
        var minEnd = startLength - start;
        for (end = 1; end <= minEnd && startValue[startLength - end] === endValue[endLength - end]; end++) ;
        return fallbackText = endValue.slice(start, 1 < end ? 1 - end : void 0);
      }
      function getEventCharCode(nativeEvent) {
        var keyCode = nativeEvent.keyCode;
        "charCode" in nativeEvent ? (nativeEvent = nativeEvent.charCode, 0 === nativeEvent && 13 === keyCode && (nativeEvent = 13)) : nativeEvent = keyCode;
        10 === nativeEvent && (nativeEvent = 13);
        return 32 <= nativeEvent || 13 === nativeEvent ? nativeEvent : 0;
      }
      function functionThatReturnsTrue() {
        return true;
      }
      function functionThatReturnsFalse() {
        return false;
      }
      function createSyntheticEvent(Interface) {
        function SyntheticBaseEvent(reactName, reactEventType, targetInst, nativeEvent, nativeEventTarget) {
          this._reactName = reactName;
          this._targetInst = targetInst;
          this.type = reactEventType;
          this.nativeEvent = nativeEvent;
          this.target = nativeEventTarget;
          this.currentTarget = null;
          for (var propName in Interface)
            Interface.hasOwnProperty(propName) && (reactName = Interface[propName], this[propName] = reactName ? reactName(nativeEvent) : nativeEvent[propName]);
          this.isDefaultPrevented = (null != nativeEvent.defaultPrevented ? nativeEvent.defaultPrevented : false === nativeEvent.returnValue) ? functionThatReturnsTrue : functionThatReturnsFalse;
          this.isPropagationStopped = functionThatReturnsFalse;
          return this;
        }
        assign(SyntheticBaseEvent.prototype, {
          preventDefault: function() {
            this.defaultPrevented = true;
            var event = this.nativeEvent;
            event && (event.preventDefault ? event.preventDefault() : "unknown" !== typeof event.returnValue && (event.returnValue = false), this.isDefaultPrevented = functionThatReturnsTrue);
          },
          stopPropagation: function() {
            var event = this.nativeEvent;
            event && (event.stopPropagation ? event.stopPropagation() : "unknown" !== typeof event.cancelBubble && (event.cancelBubble = true), this.isPropagationStopped = functionThatReturnsTrue);
          },
          persist: function() {
          },
          isPersistent: functionThatReturnsTrue
        });
        return SyntheticBaseEvent;
      }
      var EventInterface = {
        eventPhase: 0,
        bubbles: 0,
        cancelable: 0,
        timeStamp: function(event) {
          return event.timeStamp || Date.now();
        },
        defaultPrevented: 0,
        isTrusted: 0
      };
      var SyntheticEvent = createSyntheticEvent(EventInterface);
      var UIEventInterface = assign({}, EventInterface, { view: 0, detail: 0 });
      var SyntheticUIEvent = createSyntheticEvent(UIEventInterface);
      var lastMovementX;
      var lastMovementY;
      var lastMouseEvent;
      var MouseEventInterface = assign({}, UIEventInterface, {
        screenX: 0,
        screenY: 0,
        clientX: 0,
        clientY: 0,
        pageX: 0,
        pageY: 0,
        ctrlKey: 0,
        shiftKey: 0,
        altKey: 0,
        metaKey: 0,
        getModifierState: getEventModifierState,
        button: 0,
        buttons: 0,
        relatedTarget: function(event) {
          return void 0 === event.relatedTarget ? event.fromElement === event.srcElement ? event.toElement : event.fromElement : event.relatedTarget;
        },
        movementX: function(event) {
          if ("movementX" in event) return event.movementX;
          event !== lastMouseEvent && (lastMouseEvent && "mousemove" === event.type ? (lastMovementX = event.screenX - lastMouseEvent.screenX, lastMovementY = event.screenY - lastMouseEvent.screenY) : lastMovementY = lastMovementX = 0, lastMouseEvent = event);
          return lastMovementX;
        },
        movementY: function(event) {
          return "movementY" in event ? event.movementY : lastMovementY;
        }
      });
      var SyntheticMouseEvent = createSyntheticEvent(MouseEventInterface);
      var DragEventInterface = assign({}, MouseEventInterface, { dataTransfer: 0 });
      var SyntheticDragEvent = createSyntheticEvent(DragEventInterface);
      var FocusEventInterface = assign({}, UIEventInterface, { relatedTarget: 0 });
      var SyntheticFocusEvent = createSyntheticEvent(FocusEventInterface);
      var AnimationEventInterface = assign({}, EventInterface, {
        animationName: 0,
        elapsedTime: 0,
        pseudoElement: 0
      });
      var SyntheticAnimationEvent = createSyntheticEvent(AnimationEventInterface);
      var ClipboardEventInterface = assign({}, EventInterface, {
        clipboardData: function(event) {
          return "clipboardData" in event ? event.clipboardData : window.clipboardData;
        }
      });
      var SyntheticClipboardEvent = createSyntheticEvent(ClipboardEventInterface);
      var CompositionEventInterface = assign({}, EventInterface, { data: 0 });
      var SyntheticCompositionEvent = createSyntheticEvent(CompositionEventInterface);
      var normalizeKey = {
        Esc: "Escape",
        Spacebar: " ",
        Left: "ArrowLeft",
        Up: "ArrowUp",
        Right: "ArrowRight",
        Down: "ArrowDown",
        Del: "Delete",
        Win: "OS",
        Menu: "ContextMenu",
        Apps: "ContextMenu",
        Scroll: "ScrollLock",
        MozPrintableKey: "Unidentified"
      };
      var translateToKey = {
        8: "Backspace",
        9: "Tab",
        12: "Clear",
        13: "Enter",
        16: "Shift",
        17: "Control",
        18: "Alt",
        19: "Pause",
        20: "CapsLock",
        27: "Escape",
        32: " ",
        33: "PageUp",
        34: "PageDown",
        35: "End",
        36: "Home",
        37: "ArrowLeft",
        38: "ArrowUp",
        39: "ArrowRight",
        40: "ArrowDown",
        45: "Insert",
        46: "Delete",
        112: "F1",
        113: "F2",
        114: "F3",
        115: "F4",
        116: "F5",
        117: "F6",
        118: "F7",
        119: "F8",
        120: "F9",
        121: "F10",
        122: "F11",
        123: "F12",
        144: "NumLock",
        145: "ScrollLock",
        224: "Meta"
      };
      var modifierKeyToProp = {
        Alt: "altKey",
        Control: "ctrlKey",
        Meta: "metaKey",
        Shift: "shiftKey"
      };
      function modifierStateGetter(keyArg) {
        var nativeEvent = this.nativeEvent;
        return nativeEvent.getModifierState ? nativeEvent.getModifierState(keyArg) : (keyArg = modifierKeyToProp[keyArg]) ? !!nativeEvent[keyArg] : false;
      }
      function getEventModifierState() {
        return modifierStateGetter;
      }
      var KeyboardEventInterface = assign({}, UIEventInterface, {
        key: function(nativeEvent) {
          if (nativeEvent.key) {
            var key = normalizeKey[nativeEvent.key] || nativeEvent.key;
            if ("Unidentified" !== key) return key;
          }
          return "keypress" === nativeEvent.type ? (nativeEvent = getEventCharCode(nativeEvent), 13 === nativeEvent ? "Enter" : String.fromCharCode(nativeEvent)) : "keydown" === nativeEvent.type || "keyup" === nativeEvent.type ? translateToKey[nativeEvent.keyCode] || "Unidentified" : "";
        },
        code: 0,
        location: 0,
        ctrlKey: 0,
        shiftKey: 0,
        altKey: 0,
        metaKey: 0,
        repeat: 0,
        locale: 0,
        getModifierState: getEventModifierState,
        charCode: function(event) {
          return "keypress" === event.type ? getEventCharCode(event) : 0;
        },
        keyCode: function(event) {
          return "keydown" === event.type || "keyup" === event.type ? event.keyCode : 0;
        },
        which: function(event) {
          return "keypress" === event.type ? getEventCharCode(event) : "keydown" === event.type || "keyup" === event.type ? event.keyCode : 0;
        }
      });
      var SyntheticKeyboardEvent = createSyntheticEvent(KeyboardEventInterface);
      var PointerEventInterface = assign({}, MouseEventInterface, {
        pointerId: 0,
        width: 0,
        height: 0,
        pressure: 0,
        tangentialPressure: 0,
        tiltX: 0,
        tiltY: 0,
        twist: 0,
        pointerType: 0,
        isPrimary: 0
      });
      var SyntheticPointerEvent = createSyntheticEvent(PointerEventInterface);
      var TouchEventInterface = assign({}, UIEventInterface, {
        touches: 0,
        targetTouches: 0,
        changedTouches: 0,
        altKey: 0,
        metaKey: 0,
        ctrlKey: 0,
        shiftKey: 0,
        getModifierState: getEventModifierState
      });
      var SyntheticTouchEvent = createSyntheticEvent(TouchEventInterface);
      var TransitionEventInterface = assign({}, EventInterface, {
        propertyName: 0,
        elapsedTime: 0,
        pseudoElement: 0
      });
      var SyntheticTransitionEvent = createSyntheticEvent(TransitionEventInterface);
      var WheelEventInterface = assign({}, MouseEventInterface, {
        deltaX: function(event) {
          return "deltaX" in event ? event.deltaX : "wheelDeltaX" in event ? -event.wheelDeltaX : 0;
        },
        deltaY: function(event) {
          return "deltaY" in event ? event.deltaY : "wheelDeltaY" in event ? -event.wheelDeltaY : "wheelDelta" in event ? -event.wheelDelta : 0;
        },
        deltaZ: 0,
        deltaMode: 0
      });
      var SyntheticWheelEvent = createSyntheticEvent(WheelEventInterface);
      var ToggleEventInterface = assign({}, EventInterface, {
        newState: 0,
        oldState: 0
      });
      var SyntheticToggleEvent = createSyntheticEvent(ToggleEventInterface);
      var END_KEYCODES = [9, 13, 27, 32];
      var canUseCompositionEvent = canUseDOM && "CompositionEvent" in window;
      var documentMode = null;
      canUseDOM && "documentMode" in document && (documentMode = document.documentMode);
      var canUseTextInputEvent = canUseDOM && "TextEvent" in window && !documentMode;
      var useFallbackCompositionData = canUseDOM && (!canUseCompositionEvent || documentMode && 8 < documentMode && 11 >= documentMode);
      var SPACEBAR_CHAR = String.fromCharCode(32);
      var hasSpaceKeypress = false;
      function isFallbackCompositionEnd(domEventName, nativeEvent) {
        switch (domEventName) {
          case "keyup":
            return -1 !== END_KEYCODES.indexOf(nativeEvent.keyCode);
          case "keydown":
            return 229 !== nativeEvent.keyCode;
          case "keypress":
          case "mousedown":
          case "focusout":
            return true;
          default:
            return false;
        }
      }
      function getDataFromCustomEvent(nativeEvent) {
        nativeEvent = nativeEvent.detail;
        return "object" === typeof nativeEvent && "data" in nativeEvent ? nativeEvent.data : null;
      }
      var isComposing = false;
      function getNativeBeforeInputChars(domEventName, nativeEvent) {
        switch (domEventName) {
          case "compositionend":
            return getDataFromCustomEvent(nativeEvent);
          case "keypress":
            if (32 !== nativeEvent.which) return null;
            hasSpaceKeypress = true;
            return SPACEBAR_CHAR;
          case "textInput":
            return domEventName = nativeEvent.data, domEventName === SPACEBAR_CHAR && hasSpaceKeypress ? null : domEventName;
          default:
            return null;
        }
      }
      function getFallbackBeforeInputChars(domEventName, nativeEvent) {
        if (isComposing)
          return "compositionend" === domEventName || !canUseCompositionEvent && isFallbackCompositionEnd(domEventName, nativeEvent) ? (domEventName = getData(), fallbackText = startText = root = null, isComposing = false, domEventName) : null;
        switch (domEventName) {
          case "paste":
            return null;
          case "keypress":
            if (!(nativeEvent.ctrlKey || nativeEvent.altKey || nativeEvent.metaKey) || nativeEvent.ctrlKey && nativeEvent.altKey) {
              if (nativeEvent.char && 1 < nativeEvent.char.length)
                return nativeEvent.char;
              if (nativeEvent.which) return String.fromCharCode(nativeEvent.which);
            }
            return null;
          case "compositionend":
            return useFallbackCompositionData && "ko" !== nativeEvent.locale ? null : nativeEvent.data;
          default:
            return null;
        }
      }
      var supportedInputTypes = {
        color: true,
        date: true,
        datetime: true,
        "datetime-local": true,
        email: true,
        month: true,
        number: true,
        password: true,
        range: true,
        search: true,
        tel: true,
        text: true,
        time: true,
        url: true,
        week: true
      };
      function isTextInputElement(elem) {
        var nodeName = elem && elem.nodeName && elem.nodeName.toLowerCase();
        return "input" === nodeName ? !!supportedInputTypes[elem.type] : "textarea" === nodeName ? true : false;
      }
      function createAndAccumulateChangeEvent(dispatchQueue, inst, nativeEvent, target) {
        restoreTarget ? restoreQueue ? restoreQueue.push(target) : restoreQueue = [target] : restoreTarget = target;
        inst = accumulateTwoPhaseListeners(inst, "onChange");
        0 < inst.length && (nativeEvent = new SyntheticEvent(
          "onChange",
          "change",
          null,
          nativeEvent,
          target
        ), dispatchQueue.push({ event: nativeEvent, listeners: inst }));
      }
      var activeElement$1 = null;
      var activeElementInst$1 = null;
      function runEventInBatch(dispatchQueue) {
        processDispatchQueue(dispatchQueue, 0);
      }
      function getInstIfValueChanged(targetInst) {
        var targetNode = getNodeFromInstance(targetInst);
        if (updateValueIfChanged(targetNode)) return targetInst;
      }
      function getTargetInstForChangeEvent(domEventName, targetInst) {
        if ("change" === domEventName) return targetInst;
      }
      var isInputEventSupported = false;
      if (canUseDOM) {
        if (canUseDOM) {
          isSupported$jscomp$inline_427 = "oninput" in document;
          if (!isSupported$jscomp$inline_427) {
            element$jscomp$inline_428 = document.createElement("div");
            element$jscomp$inline_428.setAttribute("oninput", "return;");
            isSupported$jscomp$inline_427 = "function" === typeof element$jscomp$inline_428.oninput;
          }
          JSCompiler_inline_result$jscomp$286 = isSupported$jscomp$inline_427;
        } else JSCompiler_inline_result$jscomp$286 = false;
        isInputEventSupported = JSCompiler_inline_result$jscomp$286 && (!document.documentMode || 9 < document.documentMode);
      }
      var JSCompiler_inline_result$jscomp$286;
      var isSupported$jscomp$inline_427;
      var element$jscomp$inline_428;
      function stopWatchingForValueChange() {
        activeElement$1 && (activeElement$1.detachEvent("onpropertychange", handlePropertyChange), activeElementInst$1 = activeElement$1 = null);
      }
      function handlePropertyChange(nativeEvent) {
        if ("value" === nativeEvent.propertyName && getInstIfValueChanged(activeElementInst$1)) {
          var dispatchQueue = [];
          createAndAccumulateChangeEvent(
            dispatchQueue,
            activeElementInst$1,
            nativeEvent,
            getEventTarget(nativeEvent)
          );
          batchedUpdates$1(runEventInBatch, dispatchQueue);
        }
      }
      function handleEventsForInputEventPolyfill(domEventName, target, targetInst) {
        "focusin" === domEventName ? (stopWatchingForValueChange(), activeElement$1 = target, activeElementInst$1 = targetInst, activeElement$1.attachEvent("onpropertychange", handlePropertyChange)) : "focusout" === domEventName && stopWatchingForValueChange();
      }
      function getTargetInstForInputEventPolyfill(domEventName) {
        if ("selectionchange" === domEventName || "keyup" === domEventName || "keydown" === domEventName)
          return getInstIfValueChanged(activeElementInst$1);
      }
      function getTargetInstForClickEvent(domEventName, targetInst) {
        if ("click" === domEventName) return getInstIfValueChanged(targetInst);
      }
      function getTargetInstForInputOrChangeEvent(domEventName, targetInst) {
        if ("input" === domEventName || "change" === domEventName)
          return getInstIfValueChanged(targetInst);
      }
      function is(x, y) {
        return x === y && (0 !== x || 1 / x === 1 / y) || x !== x && y !== y;
      }
      var objectIs = "function" === typeof Object.is ? Object.is : is;
      function shallowEqual(objA, objB) {
        if (objectIs(objA, objB)) return true;
        if ("object" !== typeof objA || null === objA || "object" !== typeof objB || null === objB)
          return false;
        var keysA = Object.keys(objA), keysB = Object.keys(objB);
        if (keysA.length !== keysB.length) return false;
        for (keysB = 0; keysB < keysA.length; keysB++) {
          var currentKey = keysA[keysB];
          if (!hasOwnProperty.call(objB, currentKey) || !objectIs(objA[currentKey], objB[currentKey]))
            return false;
        }
        return true;
      }
      function getLeafNode(node) {
        for (; node && node.firstChild; ) node = node.firstChild;
        return node;
      }
      function getNodeForCharacterOffset(root2, offset) {
        var node = getLeafNode(root2);
        root2 = 0;
        for (var nodeEnd; node; ) {
          if (3 === node.nodeType) {
            nodeEnd = root2 + node.textContent.length;
            if (root2 <= offset && nodeEnd >= offset)
              return { node, offset: offset - root2 };
            root2 = nodeEnd;
          }
          a: {
            for (; node; ) {
              if (node.nextSibling) {
                node = node.nextSibling;
                break a;
              }
              node = node.parentNode;
            }
            node = void 0;
          }
          node = getLeafNode(node);
        }
      }
      function containsNode(outerNode, innerNode) {
        return outerNode && innerNode ? outerNode === innerNode ? true : outerNode && 3 === outerNode.nodeType ? false : innerNode && 3 === innerNode.nodeType ? containsNode(outerNode, innerNode.parentNode) : "contains" in outerNode ? outerNode.contains(innerNode) : outerNode.compareDocumentPosition ? !!(outerNode.compareDocumentPosition(innerNode) & 16) : false : false;
      }
      function getActiveElementDeep(containerInfo) {
        containerInfo = null != containerInfo && null != containerInfo.ownerDocument && null != containerInfo.ownerDocument.defaultView ? containerInfo.ownerDocument.defaultView : window;
        for (var element = getActiveElement(containerInfo.document); element instanceof containerInfo.HTMLIFrameElement; ) {
          try {
            var JSCompiler_inline_result = "string" === typeof element.contentWindow.location.href;
          } catch (err) {
            JSCompiler_inline_result = false;
          }
          if (JSCompiler_inline_result) containerInfo = element.contentWindow;
          else break;
          element = getActiveElement(containerInfo.document);
        }
        return element;
      }
      function hasSelectionCapabilities(elem) {
        var nodeName = elem && elem.nodeName && elem.nodeName.toLowerCase();
        return nodeName && ("input" === nodeName && ("text" === elem.type || "search" === elem.type || "tel" === elem.type || "url" === elem.type || "password" === elem.type) || "textarea" === nodeName || "true" === elem.contentEditable);
      }
      var skipSelectionChangeEvent = canUseDOM && "documentMode" in document && 11 >= document.documentMode;
      var activeElement = null;
      var activeElementInst = null;
      var lastSelection = null;
      var mouseDown = false;
      function constructSelectEvent(dispatchQueue, nativeEvent, nativeEventTarget) {
        var doc = nativeEventTarget.window === nativeEventTarget ? nativeEventTarget.document : 9 === nativeEventTarget.nodeType ? nativeEventTarget : nativeEventTarget.ownerDocument;
        mouseDown || null == activeElement || activeElement !== getActiveElement(doc) || (doc = activeElement, "selectionStart" in doc && hasSelectionCapabilities(doc) ? doc = { start: doc.selectionStart, end: doc.selectionEnd } : (doc = (doc.ownerDocument && doc.ownerDocument.defaultView || window).getSelection(), doc = {
          anchorNode: doc.anchorNode,
          anchorOffset: doc.anchorOffset,
          focusNode: doc.focusNode,
          focusOffset: doc.focusOffset
        }), lastSelection && shallowEqual(lastSelection, doc) || (lastSelection = doc, doc = accumulateTwoPhaseListeners(activeElementInst, "onSelect"), 0 < doc.length && (nativeEvent = new SyntheticEvent(
          "onSelect",
          "select",
          null,
          nativeEvent,
          nativeEventTarget
        ), dispatchQueue.push({ event: nativeEvent, listeners: doc }), nativeEvent.target = activeElement)));
      }
      function makePrefixMap(styleProp, eventName) {
        var prefixes = {};
        prefixes[styleProp.toLowerCase()] = eventName.toLowerCase();
        prefixes["Webkit" + styleProp] = "webkit" + eventName;
        prefixes["Moz" + styleProp] = "moz" + eventName;
        return prefixes;
      }
      var vendorPrefixes = {
        animationend: makePrefixMap("Animation", "AnimationEnd"),
        animationiteration: makePrefixMap("Animation", "AnimationIteration"),
        animationstart: makePrefixMap("Animation", "AnimationStart"),
        transitionrun: makePrefixMap("Transition", "TransitionRun"),
        transitionstart: makePrefixMap("Transition", "TransitionStart"),
        transitioncancel: makePrefixMap("Transition", "TransitionCancel"),
        transitionend: makePrefixMap("Transition", "TransitionEnd")
      };
      var prefixedEventNames = {};
      var style = {};
      canUseDOM && (style = document.createElement("div").style, "AnimationEvent" in window || (delete vendorPrefixes.animationend.animation, delete vendorPrefixes.animationiteration.animation, delete vendorPrefixes.animationstart.animation), "TransitionEvent" in window || delete vendorPrefixes.transitionend.transition);
      function getVendorPrefixedEventName(eventName) {
        if (prefixedEventNames[eventName]) return prefixedEventNames[eventName];
        if (!vendorPrefixes[eventName]) return eventName;
        var prefixMap = vendorPrefixes[eventName], styleProp;
        for (styleProp in prefixMap)
          if (prefixMap.hasOwnProperty(styleProp) && styleProp in style)
            return prefixedEventNames[eventName] = prefixMap[styleProp];
        return eventName;
      }
      var ANIMATION_END = getVendorPrefixedEventName("animationend");
      var ANIMATION_ITERATION = getVendorPrefixedEventName("animationiteration");
      var ANIMATION_START = getVendorPrefixedEventName("animationstart");
      var TRANSITION_RUN = getVendorPrefixedEventName("transitionrun");
      var TRANSITION_START = getVendorPrefixedEventName("transitionstart");
      var TRANSITION_CANCEL = getVendorPrefixedEventName("transitioncancel");
      var TRANSITION_END = getVendorPrefixedEventName("transitionend");
      var topLevelEventsToReactNames = /* @__PURE__ */ new Map();
      var simpleEventPluginEvents = "abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
        " "
      );
      simpleEventPluginEvents.push("scrollEnd");
      function registerSimpleEvent(domEventName, reactName) {
        topLevelEventsToReactNames.set(domEventName, reactName);
        registerTwoPhaseEvent(reactName, [domEventName]);
      }
      var reportGlobalError = "function" === typeof reportError ? reportError : function(error) {
        if ("object" === typeof window && "function" === typeof window.ErrorEvent) {
          var event = new window.ErrorEvent("error", {
            bubbles: true,
            cancelable: true,
            message: "object" === typeof error && null !== error && "string" === typeof error.message ? String(error.message) : String(error),
            error
          });
          if (!window.dispatchEvent(event)) return;
        } else if ("object" === typeof process && "function" === typeof process.emit) {
          process.emit("uncaughtException", error);
          return;
        }
        console.error(error);
      };
      var concurrentQueues = [];
      var concurrentQueuesIndex = 0;
      var concurrentlyUpdatedLanes = 0;
      function finishQueueingConcurrentUpdates() {
        for (var endIndex = concurrentQueuesIndex, i = concurrentlyUpdatedLanes = concurrentQueuesIndex = 0; i < endIndex; ) {
          var fiber = concurrentQueues[i];
          concurrentQueues[i++] = null;
          var queue = concurrentQueues[i];
          concurrentQueues[i++] = null;
          var update = concurrentQueues[i];
          concurrentQueues[i++] = null;
          var lane = concurrentQueues[i];
          concurrentQueues[i++] = null;
          if (null !== queue && null !== update) {
            var pending = queue.pending;
            null === pending ? update.next = update : (update.next = pending.next, pending.next = update);
            queue.pending = update;
          }
          0 !== lane && markUpdateLaneFromFiberToRoot(fiber, update, lane);
        }
      }
      function enqueueUpdate$1(fiber, queue, update, lane) {
        concurrentQueues[concurrentQueuesIndex++] = fiber;
        concurrentQueues[concurrentQueuesIndex++] = queue;
        concurrentQueues[concurrentQueuesIndex++] = update;
        concurrentQueues[concurrentQueuesIndex++] = lane;
        concurrentlyUpdatedLanes |= lane;
        fiber.lanes |= lane;
        fiber = fiber.alternate;
        null !== fiber && (fiber.lanes |= lane);
      }
      function enqueueConcurrentHookUpdate(fiber, queue, update, lane) {
        enqueueUpdate$1(fiber, queue, update, lane);
        return getRootForUpdatedFiber(fiber);
      }
      function enqueueConcurrentRenderForLane(fiber, lane) {
        enqueueUpdate$1(fiber, null, null, lane);
        return getRootForUpdatedFiber(fiber);
      }
      function markUpdateLaneFromFiberToRoot(sourceFiber, update, lane) {
        sourceFiber.lanes |= lane;
        var alternate = sourceFiber.alternate;
        null !== alternate && (alternate.lanes |= lane);
        for (var isHidden = false, parent = sourceFiber.return; null !== parent; )
          parent.childLanes |= lane, alternate = parent.alternate, null !== alternate && (alternate.childLanes |= lane), 22 === parent.tag && (sourceFiber = parent.stateNode, null === sourceFiber || sourceFiber._visibility & 1 || (isHidden = true)), sourceFiber = parent, parent = parent.return;
        return 3 === sourceFiber.tag ? (parent = sourceFiber.stateNode, isHidden && null !== update && (isHidden = 31 - clz32(lane), sourceFiber = parent.hiddenUpdates, alternate = sourceFiber[isHidden], null === alternate ? sourceFiber[isHidden] = [update] : alternate.push(update), update.lane = lane | 536870912), parent) : null;
      }
      function getRootForUpdatedFiber(sourceFiber) {
        if (50 < nestedUpdateCount)
          throw nestedUpdateCount = 0, rootWithNestedUpdates = null, Error(formatProdErrorMessage(185));
        for (var parent = sourceFiber.return; null !== parent; )
          sourceFiber = parent, parent = sourceFiber.return;
        return 3 === sourceFiber.tag ? sourceFiber.stateNode : null;
      }
      var emptyContextObject = {};
      function FiberNode(tag, pendingProps, key, mode) {
        this.tag = tag;
        this.key = key;
        this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null;
        this.index = 0;
        this.refCleanup = this.ref = null;
        this.pendingProps = pendingProps;
        this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null;
        this.mode = mode;
        this.subtreeFlags = this.flags = 0;
        this.deletions = null;
        this.childLanes = this.lanes = 0;
        this.alternate = null;
      }
      function createFiberImplClass(tag, pendingProps, key, mode) {
        return new FiberNode(tag, pendingProps, key, mode);
      }
      function shouldConstruct(Component) {
        Component = Component.prototype;
        return !(!Component || !Component.isReactComponent);
      }
      function createWorkInProgress(current, pendingProps) {
        var workInProgress2 = current.alternate;
        null === workInProgress2 ? (workInProgress2 = createFiberImplClass(
          current.tag,
          pendingProps,
          current.key,
          current.mode
        ), workInProgress2.elementType = current.elementType, workInProgress2.type = current.type, workInProgress2.stateNode = current.stateNode, workInProgress2.alternate = current, current.alternate = workInProgress2) : (workInProgress2.pendingProps = pendingProps, workInProgress2.type = current.type, workInProgress2.flags = 0, workInProgress2.subtreeFlags = 0, workInProgress2.deletions = null);
        workInProgress2.flags = current.flags & 65011712;
        workInProgress2.childLanes = current.childLanes;
        workInProgress2.lanes = current.lanes;
        workInProgress2.child = current.child;
        workInProgress2.memoizedProps = current.memoizedProps;
        workInProgress2.memoizedState = current.memoizedState;
        workInProgress2.updateQueue = current.updateQueue;
        pendingProps = current.dependencies;
        workInProgress2.dependencies = null === pendingProps ? null : { lanes: pendingProps.lanes, firstContext: pendingProps.firstContext };
        workInProgress2.sibling = current.sibling;
        workInProgress2.index = current.index;
        workInProgress2.ref = current.ref;
        workInProgress2.refCleanup = current.refCleanup;
        return workInProgress2;
      }
      function resetWorkInProgress(workInProgress2, renderLanes2) {
        workInProgress2.flags &= 65011714;
        var current = workInProgress2.alternate;
        null === current ? (workInProgress2.childLanes = 0, workInProgress2.lanes = renderLanes2, workInProgress2.child = null, workInProgress2.subtreeFlags = 0, workInProgress2.memoizedProps = null, workInProgress2.memoizedState = null, workInProgress2.updateQueue = null, workInProgress2.dependencies = null, workInProgress2.stateNode = null) : (workInProgress2.childLanes = current.childLanes, workInProgress2.lanes = current.lanes, workInProgress2.child = current.child, workInProgress2.subtreeFlags = 0, workInProgress2.deletions = null, workInProgress2.memoizedProps = current.memoizedProps, workInProgress2.memoizedState = current.memoizedState, workInProgress2.updateQueue = current.updateQueue, workInProgress2.type = current.type, renderLanes2 = current.dependencies, workInProgress2.dependencies = null === renderLanes2 ? null : {
          lanes: renderLanes2.lanes,
          firstContext: renderLanes2.firstContext
        });
        return workInProgress2;
      }
      function createFiberFromTypeAndProps(type, key, pendingProps, owner, mode, lanes) {
        var fiberTag = 0;
        owner = type;
        if ("function" === typeof type) shouldConstruct(type) && (fiberTag = 1);
        else if ("string" === typeof type)
          fiberTag = isHostHoistableType(
            type,
            pendingProps,
            contextStackCursor.current
          ) ? 26 : "html" === type || "head" === type || "body" === type ? 27 : 5;
        else
          a: switch (type) {
            case REACT_ACTIVITY_TYPE:
              return type = createFiberImplClass(31, pendingProps, key, mode), type.elementType = REACT_ACTIVITY_TYPE, type.lanes = lanes, type;
            case REACT_FRAGMENT_TYPE:
              return createFiberFromFragment(pendingProps.children, mode, lanes, key);
            case REACT_STRICT_MODE_TYPE:
              fiberTag = 8;
              mode |= 24;
              break;
            case REACT_PROFILER_TYPE:
              return type = createFiberImplClass(12, pendingProps, key, mode | 2), type.elementType = REACT_PROFILER_TYPE, type.lanes = lanes, type;
            case REACT_SUSPENSE_TYPE:
              return type = createFiberImplClass(13, pendingProps, key, mode), type.elementType = REACT_SUSPENSE_TYPE, type.lanes = lanes, type;
            case REACT_SUSPENSE_LIST_TYPE:
              return type = createFiberImplClass(19, pendingProps, key, mode), type.elementType = REACT_SUSPENSE_LIST_TYPE, type.lanes = lanes, type;
            default:
              if ("object" === typeof type && null !== type)
                switch (type.$$typeof) {
                  case REACT_CONTEXT_TYPE:
                    fiberTag = 10;
                    break a;
                  case REACT_CONSUMER_TYPE:
                    fiberTag = 9;
                    break a;
                  case REACT_FORWARD_REF_TYPE:
                    fiberTag = 11;
                    break a;
                  case REACT_MEMO_TYPE:
                    fiberTag = 14;
                    break a;
                  case REACT_LAZY_TYPE:
                    fiberTag = 16;
                    owner = null;
                    break a;
                }
              fiberTag = 29;
              pendingProps = Error(
                formatProdErrorMessage(130, null === type ? "null" : typeof type, "")
              );
              owner = null;
          }
        key = createFiberImplClass(fiberTag, pendingProps, key, mode);
        key.elementType = type;
        key.type = owner;
        key.lanes = lanes;
        return key;
      }
      function createFiberFromFragment(elements, mode, lanes, key) {
        elements = createFiberImplClass(7, elements, key, mode);
        elements.lanes = lanes;
        return elements;
      }
      function createFiberFromText(content, mode, lanes) {
        content = createFiberImplClass(6, content, null, mode);
        content.lanes = lanes;
        return content;
      }
      function createFiberFromDehydratedFragment(dehydratedNode) {
        var fiber = createFiberImplClass(18, null, null, 0);
        fiber.stateNode = dehydratedNode;
        return fiber;
      }
      function createFiberFromPortal(portal, mode, lanes) {
        mode = createFiberImplClass(
          4,
          null !== portal.children ? portal.children : [],
          portal.key,
          mode
        );
        mode.lanes = lanes;
        mode.stateNode = {
          containerInfo: portal.containerInfo,
          pendingChildren: null,
          implementation: portal.implementation
        };
        return mode;
      }
      var CapturedStacks = /* @__PURE__ */ new WeakMap();
      function createCapturedValueAtFiber(value, source) {
        if ("object" === typeof value && null !== value) {
          var existing = CapturedStacks.get(value);
          if (void 0 !== existing) return existing;
          source = {
            value,
            source,
            stack: getStackByFiberInDevAndProd(source)
          };
          CapturedStacks.set(value, source);
          return source;
        }
        return {
          value,
          source,
          stack: getStackByFiberInDevAndProd(source)
        };
      }
      var forkStack = [];
      var forkStackIndex = 0;
      var treeForkProvider = null;
      var treeForkCount = 0;
      var idStack = [];
      var idStackIndex = 0;
      var treeContextProvider = null;
      var treeContextId = 1;
      var treeContextOverflow = "";
      function pushTreeFork(workInProgress2, totalChildren) {
        forkStack[forkStackIndex++] = treeForkCount;
        forkStack[forkStackIndex++] = treeForkProvider;
        treeForkProvider = workInProgress2;
        treeForkCount = totalChildren;
      }
      function pushTreeId(workInProgress2, totalChildren, index2) {
        idStack[idStackIndex++] = treeContextId;
        idStack[idStackIndex++] = treeContextOverflow;
        idStack[idStackIndex++] = treeContextProvider;
        treeContextProvider = workInProgress2;
        var baseIdWithLeadingBit = treeContextId;
        workInProgress2 = treeContextOverflow;
        var baseLength = 32 - clz32(baseIdWithLeadingBit) - 1;
        baseIdWithLeadingBit &= ~(1 << baseLength);
        index2 += 1;
        var length = 32 - clz32(totalChildren) + baseLength;
        if (30 < length) {
          var numberOfOverflowBits = baseLength - baseLength % 5;
          length = (baseIdWithLeadingBit & (1 << numberOfOverflowBits) - 1).toString(32);
          baseIdWithLeadingBit >>= numberOfOverflowBits;
          baseLength -= numberOfOverflowBits;
          treeContextId = 1 << 32 - clz32(totalChildren) + baseLength | index2 << baseLength | baseIdWithLeadingBit;
          treeContextOverflow = length + workInProgress2;
        } else
          treeContextId = 1 << length | index2 << baseLength | baseIdWithLeadingBit, treeContextOverflow = workInProgress2;
      }
      function pushMaterializedTreeId(workInProgress2) {
        null !== workInProgress2.return && (pushTreeFork(workInProgress2, 1), pushTreeId(workInProgress2, 1, 0));
      }
      function popTreeContext(workInProgress2) {
        for (; workInProgress2 === treeForkProvider; )
          treeForkProvider = forkStack[--forkStackIndex], forkStack[forkStackIndex] = null, treeForkCount = forkStack[--forkStackIndex], forkStack[forkStackIndex] = null;
        for (; workInProgress2 === treeContextProvider; )
          treeContextProvider = idStack[--idStackIndex], idStack[idStackIndex] = null, treeContextOverflow = idStack[--idStackIndex], idStack[idStackIndex] = null, treeContextId = idStack[--idStackIndex], idStack[idStackIndex] = null;
      }
      function restoreSuspendedTreeContext(workInProgress2, suspendedContext) {
        idStack[idStackIndex++] = treeContextId;
        idStack[idStackIndex++] = treeContextOverflow;
        idStack[idStackIndex++] = treeContextProvider;
        treeContextId = suspendedContext.id;
        treeContextOverflow = suspendedContext.overflow;
        treeContextProvider = workInProgress2;
      }
      var hydrationParentFiber = null;
      var nextHydratableInstance = null;
      var isHydrating = false;
      var hydrationErrors = null;
      var rootOrSingletonContext = false;
      var HydrationMismatchException = Error(formatProdErrorMessage(519));
      function throwOnHydrationMismatch(fiber) {
        var error = Error(
          formatProdErrorMessage(
            418,
            1 < arguments.length && void 0 !== arguments[1] && arguments[1] ? "text" : "HTML",
            ""
          )
        );
        queueHydrationError(createCapturedValueAtFiber(error, fiber));
        throw HydrationMismatchException;
      }
      function prepareToHydrateHostInstance(fiber) {
        var instance = fiber.stateNode, type = fiber.type, props = fiber.memoizedProps;
        instance[internalInstanceKey] = fiber;
        instance[internalPropsKey] = props;
        switch (type) {
          case "dialog":
            listenToNonDelegatedEvent("cancel", instance);
            listenToNonDelegatedEvent("close", instance);
            break;
          case "iframe":
          case "object":
          case "embed":
            listenToNonDelegatedEvent("load", instance);
            break;
          case "video":
          case "audio":
            for (type = 0; type < mediaEventTypes.length; type++)
              listenToNonDelegatedEvent(mediaEventTypes[type], instance);
            break;
          case "source":
            listenToNonDelegatedEvent("error", instance);
            break;
          case "img":
          case "image":
          case "link":
            listenToNonDelegatedEvent("error", instance);
            listenToNonDelegatedEvent("load", instance);
            break;
          case "details":
            listenToNonDelegatedEvent("toggle", instance);
            break;
          case "input":
            listenToNonDelegatedEvent("invalid", instance);
            initInput(
              instance,
              props.value,
              props.defaultValue,
              props.checked,
              props.defaultChecked,
              props.type,
              props.name,
              true
            );
            break;
          case "select":
            listenToNonDelegatedEvent("invalid", instance);
            break;
          case "textarea":
            listenToNonDelegatedEvent("invalid", instance), initTextarea(instance, props.value, props.defaultValue, props.children);
        }
        type = props.children;
        "string" !== typeof type && "number" !== typeof type && "bigint" !== typeof type || instance.textContent === "" + type || true === props.suppressHydrationWarning || checkForUnmatchedText(instance.textContent, type) ? (null != props.popover && (listenToNonDelegatedEvent("beforetoggle", instance), listenToNonDelegatedEvent("toggle", instance)), null != props.onScroll && listenToNonDelegatedEvent("scroll", instance), null != props.onScrollEnd && listenToNonDelegatedEvent("scrollend", instance), null != props.onClick && (instance.onclick = noop$1), instance = true) : instance = false;
        instance || throwOnHydrationMismatch(fiber, true);
      }
      function popToNextHostParent(fiber) {
        for (hydrationParentFiber = fiber.return; hydrationParentFiber; )
          switch (hydrationParentFiber.tag) {
            case 5:
            case 31:
            case 13:
              rootOrSingletonContext = false;
              return;
            case 27:
            case 3:
              rootOrSingletonContext = true;
              return;
            default:
              hydrationParentFiber = hydrationParentFiber.return;
          }
      }
      function popHydrationState(fiber) {
        if (fiber !== hydrationParentFiber) return false;
        if (!isHydrating) return popToNextHostParent(fiber), isHydrating = true, false;
        var tag = fiber.tag, JSCompiler_temp;
        if (JSCompiler_temp = 3 !== tag && 27 !== tag) {
          if (JSCompiler_temp = 5 === tag)
            JSCompiler_temp = fiber.type, JSCompiler_temp = !("form" !== JSCompiler_temp && "button" !== JSCompiler_temp) || shouldSetTextContent(fiber.type, fiber.memoizedProps);
          JSCompiler_temp = !JSCompiler_temp;
        }
        JSCompiler_temp && nextHydratableInstance && throwOnHydrationMismatch(fiber);
        popToNextHostParent(fiber);
        if (13 === tag) {
          fiber = fiber.memoizedState;
          fiber = null !== fiber ? fiber.dehydrated : null;
          if (!fiber) throw Error(formatProdErrorMessage(317));
          nextHydratableInstance = getNextHydratableInstanceAfterHydrationBoundary(fiber);
        } else if (31 === tag) {
          fiber = fiber.memoizedState;
          fiber = null !== fiber ? fiber.dehydrated : null;
          if (!fiber) throw Error(formatProdErrorMessage(317));
          nextHydratableInstance = getNextHydratableInstanceAfterHydrationBoundary(fiber);
        } else
          27 === tag ? (tag = nextHydratableInstance, isSingletonScope(fiber.type) ? (fiber = previousHydratableOnEnteringScopedSingleton, previousHydratableOnEnteringScopedSingleton = null, nextHydratableInstance = fiber) : nextHydratableInstance = tag) : nextHydratableInstance = hydrationParentFiber ? getNextHydratable(fiber.stateNode.nextSibling) : null;
        return true;
      }
      function resetHydrationState() {
        nextHydratableInstance = hydrationParentFiber = null;
        isHydrating = false;
      }
      function upgradeHydrationErrorsToRecoverable() {
        var queuedErrors = hydrationErrors;
        null !== queuedErrors && (null === workInProgressRootRecoverableErrors ? workInProgressRootRecoverableErrors = queuedErrors : workInProgressRootRecoverableErrors.push.apply(
          workInProgressRootRecoverableErrors,
          queuedErrors
        ), hydrationErrors = null);
        return queuedErrors;
      }
      function queueHydrationError(error) {
        null === hydrationErrors ? hydrationErrors = [error] : hydrationErrors.push(error);
      }
      var valueCursor = createCursor(null);
      var currentlyRenderingFiber$1 = null;
      var lastContextDependency = null;
      function pushProvider(providerFiber, context, nextValue) {
        push(valueCursor, context._currentValue);
        context._currentValue = nextValue;
      }
      function popProvider(context) {
        context._currentValue = valueCursor.current;
        pop(valueCursor);
      }
      function scheduleContextWorkOnParentPath(parent, renderLanes2, propagationRoot) {
        for (; null !== parent; ) {
          var alternate = parent.alternate;
          (parent.childLanes & renderLanes2) !== renderLanes2 ? (parent.childLanes |= renderLanes2, null !== alternate && (alternate.childLanes |= renderLanes2)) : null !== alternate && (alternate.childLanes & renderLanes2) !== renderLanes2 && (alternate.childLanes |= renderLanes2);
          if (parent === propagationRoot) break;
          parent = parent.return;
        }
      }
      function propagateContextChanges(workInProgress2, contexts, renderLanes2, forcePropagateEntireTree) {
        var fiber = workInProgress2.child;
        null !== fiber && (fiber.return = workInProgress2);
        for (; null !== fiber; ) {
          var list = fiber.dependencies;
          if (null !== list) {
            var nextFiber = fiber.child;
            list = list.firstContext;
            a: for (; null !== list; ) {
              var dependency = list;
              list = fiber;
              for (var i = 0; i < contexts.length; i++)
                if (dependency.context === contexts[i]) {
                  list.lanes |= renderLanes2;
                  dependency = list.alternate;
                  null !== dependency && (dependency.lanes |= renderLanes2);
                  scheduleContextWorkOnParentPath(
                    list.return,
                    renderLanes2,
                    workInProgress2
                  );
                  forcePropagateEntireTree || (nextFiber = null);
                  break a;
                }
              list = dependency.next;
            }
          } else if (18 === fiber.tag) {
            nextFiber = fiber.return;
            if (null === nextFiber) throw Error(formatProdErrorMessage(341));
            nextFiber.lanes |= renderLanes2;
            list = nextFiber.alternate;
            null !== list && (list.lanes |= renderLanes2);
            scheduleContextWorkOnParentPath(nextFiber, renderLanes2, workInProgress2);
            nextFiber = null;
          } else nextFiber = fiber.child;
          if (null !== nextFiber) nextFiber.return = fiber;
          else
            for (nextFiber = fiber; null !== nextFiber; ) {
              if (nextFiber === workInProgress2) {
                nextFiber = null;
                break;
              }
              fiber = nextFiber.sibling;
              if (null !== fiber) {
                fiber.return = nextFiber.return;
                nextFiber = fiber;
                break;
              }
              nextFiber = nextFiber.return;
            }
          fiber = nextFiber;
        }
      }
      function propagateParentContextChanges(current, workInProgress2, renderLanes2, forcePropagateEntireTree) {
        current = null;
        for (var parent = workInProgress2, isInsidePropagationBailout = false; null !== parent; ) {
          if (!isInsidePropagationBailout) {
            if (0 !== (parent.flags & 524288)) isInsidePropagationBailout = true;
            else if (0 !== (parent.flags & 262144)) break;
          }
          if (10 === parent.tag) {
            var currentParent = parent.alternate;
            if (null === currentParent) throw Error(formatProdErrorMessage(387));
            currentParent = currentParent.memoizedProps;
            if (null !== currentParent) {
              var context = parent.type;
              objectIs(parent.pendingProps.value, currentParent.value) || (null !== current ? current.push(context) : current = [context]);
            }
          } else if (parent === hostTransitionProviderCursor.current) {
            currentParent = parent.alternate;
            if (null === currentParent) throw Error(formatProdErrorMessage(387));
            currentParent.memoizedState.memoizedState !== parent.memoizedState.memoizedState && (null !== current ? current.push(HostTransitionContext) : current = [HostTransitionContext]);
          }
          parent = parent.return;
        }
        null !== current && propagateContextChanges(
          workInProgress2,
          current,
          renderLanes2,
          forcePropagateEntireTree
        );
        workInProgress2.flags |= 262144;
      }
      function checkIfContextChanged(currentDependencies) {
        for (currentDependencies = currentDependencies.firstContext; null !== currentDependencies; ) {
          if (!objectIs(
            currentDependencies.context._currentValue,
            currentDependencies.memoizedValue
          ))
            return true;
          currentDependencies = currentDependencies.next;
        }
        return false;
      }
      function prepareToReadContext(workInProgress2) {
        currentlyRenderingFiber$1 = workInProgress2;
        lastContextDependency = null;
        workInProgress2 = workInProgress2.dependencies;
        null !== workInProgress2 && (workInProgress2.firstContext = null);
      }
      function readContext(context) {
        return readContextForConsumer(currentlyRenderingFiber$1, context);
      }
      function readContextDuringReconciliation(consumer, context) {
        null === currentlyRenderingFiber$1 && prepareToReadContext(consumer);
        return readContextForConsumer(consumer, context);
      }
      function readContextForConsumer(consumer, context) {
        var value = context._currentValue;
        context = { context, memoizedValue: value, next: null };
        if (null === lastContextDependency) {
          if (null === consumer) throw Error(formatProdErrorMessage(308));
          lastContextDependency = context;
          consumer.dependencies = { lanes: 0, firstContext: context };
          consumer.flags |= 524288;
        } else lastContextDependency = lastContextDependency.next = context;
        return value;
      }
      var AbortControllerLocal = "undefined" !== typeof AbortController ? AbortController : function() {
        var listeners = [], signal = this.signal = {
          aborted: false,
          addEventListener: function(type, listener) {
            listeners.push(listener);
          }
        };
        this.abort = function() {
          signal.aborted = true;
          listeners.forEach(function(listener) {
            return listener();
          });
        };
      };
      var scheduleCallback$2 = Scheduler.unstable_scheduleCallback;
      var NormalPriority = Scheduler.unstable_NormalPriority;
      var CacheContext = {
        $$typeof: REACT_CONTEXT_TYPE,
        Consumer: null,
        Provider: null,
        _currentValue: null,
        _currentValue2: null,
        _threadCount: 0
      };
      function createCache() {
        return {
          controller: new AbortControllerLocal(),
          data: /* @__PURE__ */ new Map(),
          refCount: 0
        };
      }
      function releaseCache(cache2) {
        cache2.refCount--;
        0 === cache2.refCount && scheduleCallback$2(NormalPriority, function() {
          cache2.controller.abort();
        });
      }
      var currentEntangledListeners = null;
      var currentEntangledPendingCount = 0;
      var currentEntangledLane = 0;
      var currentEntangledActionThenable = null;
      function entangleAsyncAction(transition, thenable) {
        if (null === currentEntangledListeners) {
          var entangledListeners = currentEntangledListeners = [];
          currentEntangledPendingCount = 0;
          currentEntangledLane = requestTransitionLane();
          currentEntangledActionThenable = {
            status: "pending",
            value: void 0,
            then: function(resolve) {
              entangledListeners.push(resolve);
            }
          };
        }
        currentEntangledPendingCount++;
        thenable.then(pingEngtangledActionScope, pingEngtangledActionScope);
        return thenable;
      }
      function pingEngtangledActionScope() {
        if (0 === --currentEntangledPendingCount && null !== currentEntangledListeners) {
          null !== currentEntangledActionThenable && (currentEntangledActionThenable.status = "fulfilled");
          var listeners = currentEntangledListeners;
          currentEntangledListeners = null;
          currentEntangledLane = 0;
          currentEntangledActionThenable = null;
          for (var i = 0; i < listeners.length; i++) (0, listeners[i])();
        }
      }
      function chainThenableValue(thenable, result) {
        var listeners = [], thenableWithOverride = {
          status: "pending",
          value: null,
          reason: null,
          then: function(resolve) {
            listeners.push(resolve);
          }
        };
        thenable.then(
          function() {
            thenableWithOverride.status = "fulfilled";
            thenableWithOverride.value = result;
            for (var i = 0; i < listeners.length; i++) (0, listeners[i])(result);
          },
          function(error) {
            thenableWithOverride.status = "rejected";
            thenableWithOverride.reason = error;
            for (error = 0; error < listeners.length; error++)
              (0, listeners[error])(void 0);
          }
        );
        return thenableWithOverride;
      }
      var prevOnStartTransitionFinish = ReactSharedInternals.S;
      ReactSharedInternals.S = function(transition, returnValue) {
        globalMostRecentTransitionTime = now();
        "object" === typeof returnValue && null !== returnValue && "function" === typeof returnValue.then && entangleAsyncAction(transition, returnValue);
        null !== prevOnStartTransitionFinish && prevOnStartTransitionFinish(transition, returnValue);
      };
      var resumedCache = createCursor(null);
      function peekCacheFromPool() {
        var cacheResumedFromPreviousRender = resumedCache.current;
        return null !== cacheResumedFromPreviousRender ? cacheResumedFromPreviousRender : workInProgressRoot.pooledCache;
      }
      function pushTransition(offscreenWorkInProgress, prevCachePool) {
        null === prevCachePool ? push(resumedCache, resumedCache.current) : push(resumedCache, prevCachePool.pool);
      }
      function getSuspendedCache() {
        var cacheFromPool = peekCacheFromPool();
        return null === cacheFromPool ? null : { parent: CacheContext._currentValue, pool: cacheFromPool };
      }
      var SuspenseException = Error(formatProdErrorMessage(460));
      var SuspenseyCommitException = Error(formatProdErrorMessage(474));
      var SuspenseActionException = Error(formatProdErrorMessage(542));
      var noopSuspenseyCommitThenable = { then: function() {
      } };
      function isThenableResolved(thenable) {
        thenable = thenable.status;
        return "fulfilled" === thenable || "rejected" === thenable;
      }
      function trackUsedThenable(thenableState2, thenable, index2) {
        index2 = thenableState2[index2];
        void 0 === index2 ? thenableState2.push(thenable) : index2 !== thenable && (thenable.then(noop$1, noop$1), thenable = index2);
        switch (thenable.status) {
          case "fulfilled":
            return thenable.value;
          case "rejected":
            throw thenableState2 = thenable.reason, checkIfUseWrappedInAsyncCatch(thenableState2), thenableState2;
          default:
            if ("string" === typeof thenable.status) thenable.then(noop$1, noop$1);
            else {
              thenableState2 = workInProgressRoot;
              if (null !== thenableState2 && 100 < thenableState2.shellSuspendCounter)
                throw Error(formatProdErrorMessage(482));
              thenableState2 = thenable;
              thenableState2.status = "pending";
              thenableState2.then(
                function(fulfilledValue) {
                  if ("pending" === thenable.status) {
                    var fulfilledThenable = thenable;
                    fulfilledThenable.status = "fulfilled";
                    fulfilledThenable.value = fulfilledValue;
                  }
                },
                function(error) {
                  if ("pending" === thenable.status) {
                    var rejectedThenable = thenable;
                    rejectedThenable.status = "rejected";
                    rejectedThenable.reason = error;
                  }
                }
              );
            }
            switch (thenable.status) {
              case "fulfilled":
                return thenable.value;
              case "rejected":
                throw thenableState2 = thenable.reason, checkIfUseWrappedInAsyncCatch(thenableState2), thenableState2;
            }
            suspendedThenable = thenable;
            throw SuspenseException;
        }
      }
      function resolveLazy(lazyType) {
        try {
          var init = lazyType._init;
          return init(lazyType._payload);
        } catch (x) {
          if (null !== x && "object" === typeof x && "function" === typeof x.then)
            throw suspendedThenable = x, SuspenseException;
          throw x;
        }
      }
      var suspendedThenable = null;
      function getSuspendedThenable() {
        if (null === suspendedThenable) throw Error(formatProdErrorMessage(459));
        var thenable = suspendedThenable;
        suspendedThenable = null;
        return thenable;
      }
      function checkIfUseWrappedInAsyncCatch(rejectedReason) {
        if (rejectedReason === SuspenseException || rejectedReason === SuspenseActionException)
          throw Error(formatProdErrorMessage(483));
      }
      var thenableState$1 = null;
      var thenableIndexCounter$1 = 0;
      function unwrapThenable(thenable) {
        var index2 = thenableIndexCounter$1;
        thenableIndexCounter$1 += 1;
        null === thenableState$1 && (thenableState$1 = []);
        return trackUsedThenable(thenableState$1, thenable, index2);
      }
      function coerceRef(workInProgress2, element) {
        element = element.props.ref;
        workInProgress2.ref = void 0 !== element ? element : null;
      }
      function throwOnInvalidObjectTypeImpl(returnFiber, newChild) {
        if (newChild.$$typeof === REACT_LEGACY_ELEMENT_TYPE)
          throw Error(formatProdErrorMessage(525));
        returnFiber = Object.prototype.toString.call(newChild);
        throw Error(
          formatProdErrorMessage(
            31,
            "[object Object]" === returnFiber ? "object with keys {" + Object.keys(newChild).join(", ") + "}" : returnFiber
          )
        );
      }
      function createChildReconciler(shouldTrackSideEffects) {
        function deleteChild(returnFiber, childToDelete) {
          if (shouldTrackSideEffects) {
            var deletions = returnFiber.deletions;
            null === deletions ? (returnFiber.deletions = [childToDelete], returnFiber.flags |= 16) : deletions.push(childToDelete);
          }
        }
        function deleteRemainingChildren(returnFiber, currentFirstChild) {
          if (!shouldTrackSideEffects) return null;
          for (; null !== currentFirstChild; )
            deleteChild(returnFiber, currentFirstChild), currentFirstChild = currentFirstChild.sibling;
          return null;
        }
        function mapRemainingChildren(currentFirstChild) {
          for (var existingChildren = /* @__PURE__ */ new Map(); null !== currentFirstChild; )
            null !== currentFirstChild.key ? existingChildren.set(currentFirstChild.key, currentFirstChild) : existingChildren.set(currentFirstChild.index, currentFirstChild), currentFirstChild = currentFirstChild.sibling;
          return existingChildren;
        }
        function useFiber(fiber, pendingProps) {
          fiber = createWorkInProgress(fiber, pendingProps);
          fiber.index = 0;
          fiber.sibling = null;
          return fiber;
        }
        function placeChild(newFiber, lastPlacedIndex, newIndex) {
          newFiber.index = newIndex;
          if (!shouldTrackSideEffects)
            return newFiber.flags |= 1048576, lastPlacedIndex;
          newIndex = newFiber.alternate;
          if (null !== newIndex)
            return newIndex = newIndex.index, newIndex < lastPlacedIndex ? (newFiber.flags |= 67108866, lastPlacedIndex) : newIndex;
          newFiber.flags |= 67108866;
          return lastPlacedIndex;
        }
        function placeSingleChild(newFiber) {
          shouldTrackSideEffects && null === newFiber.alternate && (newFiber.flags |= 67108866);
          return newFiber;
        }
        function updateTextNode(returnFiber, current, textContent, lanes) {
          if (null === current || 6 !== current.tag)
            return current = createFiberFromText(textContent, returnFiber.mode, lanes), current.return = returnFiber, current;
          current = useFiber(current, textContent);
          current.return = returnFiber;
          return current;
        }
        function updateElement(returnFiber, current, element, lanes) {
          var elementType = element.type;
          if (elementType === REACT_FRAGMENT_TYPE)
            return updateFragment(
              returnFiber,
              current,
              element.props.children,
              lanes,
              element.key
            );
          if (null !== current && (current.elementType === elementType || "object" === typeof elementType && null !== elementType && elementType.$$typeof === REACT_LAZY_TYPE && resolveLazy(elementType) === current.type))
            return current = useFiber(current, element.props), coerceRef(current, element), current.return = returnFiber, current;
          current = createFiberFromTypeAndProps(
            element.type,
            element.key,
            element.props,
            null,
            returnFiber.mode,
            lanes
          );
          coerceRef(current, element);
          current.return = returnFiber;
          return current;
        }
        function updatePortal(returnFiber, current, portal, lanes) {
          if (null === current || 4 !== current.tag || current.stateNode.containerInfo !== portal.containerInfo || current.stateNode.implementation !== portal.implementation)
            return current = createFiberFromPortal(portal, returnFiber.mode, lanes), current.return = returnFiber, current;
          current = useFiber(current, portal.children || []);
          current.return = returnFiber;
          return current;
        }
        function updateFragment(returnFiber, current, fragment, lanes, key) {
          if (null === current || 7 !== current.tag)
            return current = createFiberFromFragment(
              fragment,
              returnFiber.mode,
              lanes,
              key
            ), current.return = returnFiber, current;
          current = useFiber(current, fragment);
          current.return = returnFiber;
          return current;
        }
        function createChild(returnFiber, newChild, lanes) {
          if ("string" === typeof newChild && "" !== newChild || "number" === typeof newChild || "bigint" === typeof newChild)
            return newChild = createFiberFromText(
              "" + newChild,
              returnFiber.mode,
              lanes
            ), newChild.return = returnFiber, newChild;
          if ("object" === typeof newChild && null !== newChild) {
            switch (newChild.$$typeof) {
              case REACT_ELEMENT_TYPE:
                return lanes = createFiberFromTypeAndProps(
                  newChild.type,
                  newChild.key,
                  newChild.props,
                  null,
                  returnFiber.mode,
                  lanes
                ), coerceRef(lanes, newChild), lanes.return = returnFiber, lanes;
              case REACT_PORTAL_TYPE:
                return newChild = createFiberFromPortal(
                  newChild,
                  returnFiber.mode,
                  lanes
                ), newChild.return = returnFiber, newChild;
              case REACT_LAZY_TYPE:
                return newChild = resolveLazy(newChild), createChild(returnFiber, newChild, lanes);
            }
            if (isArrayImpl(newChild) || getIteratorFn(newChild))
              return newChild = createFiberFromFragment(
                newChild,
                returnFiber.mode,
                lanes,
                null
              ), newChild.return = returnFiber, newChild;
            if ("function" === typeof newChild.then)
              return createChild(returnFiber, unwrapThenable(newChild), lanes);
            if (newChild.$$typeof === REACT_CONTEXT_TYPE)
              return createChild(
                returnFiber,
                readContextDuringReconciliation(returnFiber, newChild),
                lanes
              );
            throwOnInvalidObjectTypeImpl(returnFiber, newChild);
          }
          return null;
        }
        function updateSlot(returnFiber, oldFiber, newChild, lanes) {
          var key = null !== oldFiber ? oldFiber.key : null;
          if ("string" === typeof newChild && "" !== newChild || "number" === typeof newChild || "bigint" === typeof newChild)
            return null !== key ? null : updateTextNode(returnFiber, oldFiber, "" + newChild, lanes);
          if ("object" === typeof newChild && null !== newChild) {
            switch (newChild.$$typeof) {
              case REACT_ELEMENT_TYPE:
                return newChild.key === key ? updateElement(returnFiber, oldFiber, newChild, lanes) : null;
              case REACT_PORTAL_TYPE:
                return newChild.key === key ? updatePortal(returnFiber, oldFiber, newChild, lanes) : null;
              case REACT_LAZY_TYPE:
                return newChild = resolveLazy(newChild), updateSlot(returnFiber, oldFiber, newChild, lanes);
            }
            if (isArrayImpl(newChild) || getIteratorFn(newChild))
              return null !== key ? null : updateFragment(returnFiber, oldFiber, newChild, lanes, null);
            if ("function" === typeof newChild.then)
              return updateSlot(
                returnFiber,
                oldFiber,
                unwrapThenable(newChild),
                lanes
              );
            if (newChild.$$typeof === REACT_CONTEXT_TYPE)
              return updateSlot(
                returnFiber,
                oldFiber,
                readContextDuringReconciliation(returnFiber, newChild),
                lanes
              );
            throwOnInvalidObjectTypeImpl(returnFiber, newChild);
          }
          return null;
        }
        function updateFromMap(existingChildren, returnFiber, newIdx, newChild, lanes) {
          if ("string" === typeof newChild && "" !== newChild || "number" === typeof newChild || "bigint" === typeof newChild)
            return existingChildren = existingChildren.get(newIdx) || null, updateTextNode(returnFiber, existingChildren, "" + newChild, lanes);
          if ("object" === typeof newChild && null !== newChild) {
            switch (newChild.$$typeof) {
              case REACT_ELEMENT_TYPE:
                return existingChildren = existingChildren.get(
                  null === newChild.key ? newIdx : newChild.key
                ) || null, updateElement(returnFiber, existingChildren, newChild, lanes);
              case REACT_PORTAL_TYPE:
                return existingChildren = existingChildren.get(
                  null === newChild.key ? newIdx : newChild.key
                ) || null, updatePortal(returnFiber, existingChildren, newChild, lanes);
              case REACT_LAZY_TYPE:
                return newChild = resolveLazy(newChild), updateFromMap(
                  existingChildren,
                  returnFiber,
                  newIdx,
                  newChild,
                  lanes
                );
            }
            if (isArrayImpl(newChild) || getIteratorFn(newChild))
              return existingChildren = existingChildren.get(newIdx) || null, updateFragment(returnFiber, existingChildren, newChild, lanes, null);
            if ("function" === typeof newChild.then)
              return updateFromMap(
                existingChildren,
                returnFiber,
                newIdx,
                unwrapThenable(newChild),
                lanes
              );
            if (newChild.$$typeof === REACT_CONTEXT_TYPE)
              return updateFromMap(
                existingChildren,
                returnFiber,
                newIdx,
                readContextDuringReconciliation(returnFiber, newChild),
                lanes
              );
            throwOnInvalidObjectTypeImpl(returnFiber, newChild);
          }
          return null;
        }
        function reconcileChildrenArray(returnFiber, currentFirstChild, newChildren, lanes) {
          for (var resultingFirstChild = null, previousNewFiber = null, oldFiber = currentFirstChild, newIdx = currentFirstChild = 0, nextOldFiber = null; null !== oldFiber && newIdx < newChildren.length; newIdx++) {
            oldFiber.index > newIdx ? (nextOldFiber = oldFiber, oldFiber = null) : nextOldFiber = oldFiber.sibling;
            var newFiber = updateSlot(
              returnFiber,
              oldFiber,
              newChildren[newIdx],
              lanes
            );
            if (null === newFiber) {
              null === oldFiber && (oldFiber = nextOldFiber);
              break;
            }
            shouldTrackSideEffects && oldFiber && null === newFiber.alternate && deleteChild(returnFiber, oldFiber);
            currentFirstChild = placeChild(newFiber, currentFirstChild, newIdx);
            null === previousNewFiber ? resultingFirstChild = newFiber : previousNewFiber.sibling = newFiber;
            previousNewFiber = newFiber;
            oldFiber = nextOldFiber;
          }
          if (newIdx === newChildren.length)
            return deleteRemainingChildren(returnFiber, oldFiber), isHydrating && pushTreeFork(returnFiber, newIdx), resultingFirstChild;
          if (null === oldFiber) {
            for (; newIdx < newChildren.length; newIdx++)
              oldFiber = createChild(returnFiber, newChildren[newIdx], lanes), null !== oldFiber && (currentFirstChild = placeChild(
                oldFiber,
                currentFirstChild,
                newIdx
              ), null === previousNewFiber ? resultingFirstChild = oldFiber : previousNewFiber.sibling = oldFiber, previousNewFiber = oldFiber);
            isHydrating && pushTreeFork(returnFiber, newIdx);
            return resultingFirstChild;
          }
          for (oldFiber = mapRemainingChildren(oldFiber); newIdx < newChildren.length; newIdx++)
            nextOldFiber = updateFromMap(
              oldFiber,
              returnFiber,
              newIdx,
              newChildren[newIdx],
              lanes
            ), null !== nextOldFiber && (shouldTrackSideEffects && null !== nextOldFiber.alternate && oldFiber.delete(
              null === nextOldFiber.key ? newIdx : nextOldFiber.key
            ), currentFirstChild = placeChild(
              nextOldFiber,
              currentFirstChild,
              newIdx
            ), null === previousNewFiber ? resultingFirstChild = nextOldFiber : previousNewFiber.sibling = nextOldFiber, previousNewFiber = nextOldFiber);
          shouldTrackSideEffects && oldFiber.forEach(function(child) {
            return deleteChild(returnFiber, child);
          });
          isHydrating && pushTreeFork(returnFiber, newIdx);
          return resultingFirstChild;
        }
        function reconcileChildrenIterator(returnFiber, currentFirstChild, newChildren, lanes) {
          if (null == newChildren) throw Error(formatProdErrorMessage(151));
          for (var resultingFirstChild = null, previousNewFiber = null, oldFiber = currentFirstChild, newIdx = currentFirstChild = 0, nextOldFiber = null, step = newChildren.next(); null !== oldFiber && !step.done; newIdx++, step = newChildren.next()) {
            oldFiber.index > newIdx ? (nextOldFiber = oldFiber, oldFiber = null) : nextOldFiber = oldFiber.sibling;
            var newFiber = updateSlot(returnFiber, oldFiber, step.value, lanes);
            if (null === newFiber) {
              null === oldFiber && (oldFiber = nextOldFiber);
              break;
            }
            shouldTrackSideEffects && oldFiber && null === newFiber.alternate && deleteChild(returnFiber, oldFiber);
            currentFirstChild = placeChild(newFiber, currentFirstChild, newIdx);
            null === previousNewFiber ? resultingFirstChild = newFiber : previousNewFiber.sibling = newFiber;
            previousNewFiber = newFiber;
            oldFiber = nextOldFiber;
          }
          if (step.done)
            return deleteRemainingChildren(returnFiber, oldFiber), isHydrating && pushTreeFork(returnFiber, newIdx), resultingFirstChild;
          if (null === oldFiber) {
            for (; !step.done; newIdx++, step = newChildren.next())
              step = createChild(returnFiber, step.value, lanes), null !== step && (currentFirstChild = placeChild(step, currentFirstChild, newIdx), null === previousNewFiber ? resultingFirstChild = step : previousNewFiber.sibling = step, previousNewFiber = step);
            isHydrating && pushTreeFork(returnFiber, newIdx);
            return resultingFirstChild;
          }
          for (oldFiber = mapRemainingChildren(oldFiber); !step.done; newIdx++, step = newChildren.next())
            step = updateFromMap(oldFiber, returnFiber, newIdx, step.value, lanes), null !== step && (shouldTrackSideEffects && null !== step.alternate && oldFiber.delete(null === step.key ? newIdx : step.key), currentFirstChild = placeChild(step, currentFirstChild, newIdx), null === previousNewFiber ? resultingFirstChild = step : previousNewFiber.sibling = step, previousNewFiber = step);
          shouldTrackSideEffects && oldFiber.forEach(function(child) {
            return deleteChild(returnFiber, child);
          });
          isHydrating && pushTreeFork(returnFiber, newIdx);
          return resultingFirstChild;
        }
        function reconcileChildFibersImpl(returnFiber, currentFirstChild, newChild, lanes) {
          "object" === typeof newChild && null !== newChild && newChild.type === REACT_FRAGMENT_TYPE && null === newChild.key && (newChild = newChild.props.children);
          if ("object" === typeof newChild && null !== newChild) {
            switch (newChild.$$typeof) {
              case REACT_ELEMENT_TYPE:
                a: {
                  for (var key = newChild.key; null !== currentFirstChild; ) {
                    if (currentFirstChild.key === key) {
                      key = newChild.type;
                      if (key === REACT_FRAGMENT_TYPE) {
                        if (7 === currentFirstChild.tag) {
                          deleteRemainingChildren(
                            returnFiber,
                            currentFirstChild.sibling
                          );
                          lanes = useFiber(
                            currentFirstChild,
                            newChild.props.children
                          );
                          lanes.return = returnFiber;
                          returnFiber = lanes;
                          break a;
                        }
                      } else if (currentFirstChild.elementType === key || "object" === typeof key && null !== key && key.$$typeof === REACT_LAZY_TYPE && resolveLazy(key) === currentFirstChild.type) {
                        deleteRemainingChildren(
                          returnFiber,
                          currentFirstChild.sibling
                        );
                        lanes = useFiber(currentFirstChild, newChild.props);
                        coerceRef(lanes, newChild);
                        lanes.return = returnFiber;
                        returnFiber = lanes;
                        break a;
                      }
                      deleteRemainingChildren(returnFiber, currentFirstChild);
                      break;
                    } else deleteChild(returnFiber, currentFirstChild);
                    currentFirstChild = currentFirstChild.sibling;
                  }
                  newChild.type === REACT_FRAGMENT_TYPE ? (lanes = createFiberFromFragment(
                    newChild.props.children,
                    returnFiber.mode,
                    lanes,
                    newChild.key
                  ), lanes.return = returnFiber, returnFiber = lanes) : (lanes = createFiberFromTypeAndProps(
                    newChild.type,
                    newChild.key,
                    newChild.props,
                    null,
                    returnFiber.mode,
                    lanes
                  ), coerceRef(lanes, newChild), lanes.return = returnFiber, returnFiber = lanes);
                }
                return placeSingleChild(returnFiber);
              case REACT_PORTAL_TYPE:
                a: {
                  for (key = newChild.key; null !== currentFirstChild; ) {
                    if (currentFirstChild.key === key)
                      if (4 === currentFirstChild.tag && currentFirstChild.stateNode.containerInfo === newChild.containerInfo && currentFirstChild.stateNode.implementation === newChild.implementation) {
                        deleteRemainingChildren(
                          returnFiber,
                          currentFirstChild.sibling
                        );
                        lanes = useFiber(currentFirstChild, newChild.children || []);
                        lanes.return = returnFiber;
                        returnFiber = lanes;
                        break a;
                      } else {
                        deleteRemainingChildren(returnFiber, currentFirstChild);
                        break;
                      }
                    else deleteChild(returnFiber, currentFirstChild);
                    currentFirstChild = currentFirstChild.sibling;
                  }
                  lanes = createFiberFromPortal(newChild, returnFiber.mode, lanes);
                  lanes.return = returnFiber;
                  returnFiber = lanes;
                }
                return placeSingleChild(returnFiber);
              case REACT_LAZY_TYPE:
                return newChild = resolveLazy(newChild), reconcileChildFibersImpl(
                  returnFiber,
                  currentFirstChild,
                  newChild,
                  lanes
                );
            }
            if (isArrayImpl(newChild))
              return reconcileChildrenArray(
                returnFiber,
                currentFirstChild,
                newChild,
                lanes
              );
            if (getIteratorFn(newChild)) {
              key = getIteratorFn(newChild);
              if ("function" !== typeof key) throw Error(formatProdErrorMessage(150));
              newChild = key.call(newChild);
              return reconcileChildrenIterator(
                returnFiber,
                currentFirstChild,
                newChild,
                lanes
              );
            }
            if ("function" === typeof newChild.then)
              return reconcileChildFibersImpl(
                returnFiber,
                currentFirstChild,
                unwrapThenable(newChild),
                lanes
              );
            if (newChild.$$typeof === REACT_CONTEXT_TYPE)
              return reconcileChildFibersImpl(
                returnFiber,
                currentFirstChild,
                readContextDuringReconciliation(returnFiber, newChild),
                lanes
              );
            throwOnInvalidObjectTypeImpl(returnFiber, newChild);
          }
          return "string" === typeof newChild && "" !== newChild || "number" === typeof newChild || "bigint" === typeof newChild ? (newChild = "" + newChild, null !== currentFirstChild && 6 === currentFirstChild.tag ? (deleteRemainingChildren(returnFiber, currentFirstChild.sibling), lanes = useFiber(currentFirstChild, newChild), lanes.return = returnFiber, returnFiber = lanes) : (deleteRemainingChildren(returnFiber, currentFirstChild), lanes = createFiberFromText(newChild, returnFiber.mode, lanes), lanes.return = returnFiber, returnFiber = lanes), placeSingleChild(returnFiber)) : deleteRemainingChildren(returnFiber, currentFirstChild);
        }
        return function(returnFiber, currentFirstChild, newChild, lanes) {
          try {
            thenableIndexCounter$1 = 0;
            var firstChildFiber = reconcileChildFibersImpl(
              returnFiber,
              currentFirstChild,
              newChild,
              lanes
            );
            thenableState$1 = null;
            return firstChildFiber;
          } catch (x) {
            if (x === SuspenseException || x === SuspenseActionException) throw x;
            var fiber = createFiberImplClass(29, x, null, returnFiber.mode);
            fiber.lanes = lanes;
            fiber.return = returnFiber;
            return fiber;
          } finally {
          }
        };
      }
      var reconcileChildFibers = createChildReconciler(true);
      var mountChildFibers = createChildReconciler(false);
      var hasForceUpdate = false;
      function initializeUpdateQueue(fiber) {
        fiber.updateQueue = {
          baseState: fiber.memoizedState,
          firstBaseUpdate: null,
          lastBaseUpdate: null,
          shared: { pending: null, lanes: 0, hiddenCallbacks: null },
          callbacks: null
        };
      }
      function cloneUpdateQueue(current, workInProgress2) {
        current = current.updateQueue;
        workInProgress2.updateQueue === current && (workInProgress2.updateQueue = {
          baseState: current.baseState,
          firstBaseUpdate: current.firstBaseUpdate,
          lastBaseUpdate: current.lastBaseUpdate,
          shared: current.shared,
          callbacks: null
        });
      }
      function createUpdate(lane) {
        return { lane, tag: 0, payload: null, callback: null, next: null };
      }
      function enqueueUpdate(fiber, update, lane) {
        var updateQueue = fiber.updateQueue;
        if (null === updateQueue) return null;
        updateQueue = updateQueue.shared;
        if (0 !== (executionContext & 2)) {
          var pending = updateQueue.pending;
          null === pending ? update.next = update : (update.next = pending.next, pending.next = update);
          updateQueue.pending = update;
          update = getRootForUpdatedFiber(fiber);
          markUpdateLaneFromFiberToRoot(fiber, null, lane);
          return update;
        }
        enqueueUpdate$1(fiber, updateQueue, update, lane);
        return getRootForUpdatedFiber(fiber);
      }
      function entangleTransitions(root2, fiber, lane) {
        fiber = fiber.updateQueue;
        if (null !== fiber && (fiber = fiber.shared, 0 !== (lane & 4194048))) {
          var queueLanes = fiber.lanes;
          queueLanes &= root2.pendingLanes;
          lane |= queueLanes;
          fiber.lanes = lane;
          markRootEntangled(root2, lane);
        }
      }
      function enqueueCapturedUpdate(workInProgress2, capturedUpdate) {
        var queue = workInProgress2.updateQueue, current = workInProgress2.alternate;
        if (null !== current && (current = current.updateQueue, queue === current)) {
          var newFirst = null, newLast = null;
          queue = queue.firstBaseUpdate;
          if (null !== queue) {
            do {
              var clone = {
                lane: queue.lane,
                tag: queue.tag,
                payload: queue.payload,
                callback: null,
                next: null
              };
              null === newLast ? newFirst = newLast = clone : newLast = newLast.next = clone;
              queue = queue.next;
            } while (null !== queue);
            null === newLast ? newFirst = newLast = capturedUpdate : newLast = newLast.next = capturedUpdate;
          } else newFirst = newLast = capturedUpdate;
          queue = {
            baseState: current.baseState,
            firstBaseUpdate: newFirst,
            lastBaseUpdate: newLast,
            shared: current.shared,
            callbacks: current.callbacks
          };
          workInProgress2.updateQueue = queue;
          return;
        }
        workInProgress2 = queue.lastBaseUpdate;
        null === workInProgress2 ? queue.firstBaseUpdate = capturedUpdate : workInProgress2.next = capturedUpdate;
        queue.lastBaseUpdate = capturedUpdate;
      }
      var didReadFromEntangledAsyncAction = false;
      function suspendIfUpdateReadFromEntangledAsyncAction() {
        if (didReadFromEntangledAsyncAction) {
          var entangledActionThenable = currentEntangledActionThenable;
          if (null !== entangledActionThenable) throw entangledActionThenable;
        }
      }
      function processUpdateQueue(workInProgress$jscomp$0, props, instance$jscomp$0, renderLanes2) {
        didReadFromEntangledAsyncAction = false;
        var queue = workInProgress$jscomp$0.updateQueue;
        hasForceUpdate = false;
        var firstBaseUpdate = queue.firstBaseUpdate, lastBaseUpdate = queue.lastBaseUpdate, pendingQueue = queue.shared.pending;
        if (null !== pendingQueue) {
          queue.shared.pending = null;
          var lastPendingUpdate = pendingQueue, firstPendingUpdate = lastPendingUpdate.next;
          lastPendingUpdate.next = null;
          null === lastBaseUpdate ? firstBaseUpdate = firstPendingUpdate : lastBaseUpdate.next = firstPendingUpdate;
          lastBaseUpdate = lastPendingUpdate;
          var current = workInProgress$jscomp$0.alternate;
          null !== current && (current = current.updateQueue, pendingQueue = current.lastBaseUpdate, pendingQueue !== lastBaseUpdate && (null === pendingQueue ? current.firstBaseUpdate = firstPendingUpdate : pendingQueue.next = firstPendingUpdate, current.lastBaseUpdate = lastPendingUpdate));
        }
        if (null !== firstBaseUpdate) {
          var newState = queue.baseState;
          lastBaseUpdate = 0;
          current = firstPendingUpdate = lastPendingUpdate = null;
          pendingQueue = firstBaseUpdate;
          do {
            var updateLane = pendingQueue.lane & -536870913, isHiddenUpdate = updateLane !== pendingQueue.lane;
            if (isHiddenUpdate ? (workInProgressRootRenderLanes & updateLane) === updateLane : (renderLanes2 & updateLane) === updateLane) {
              0 !== updateLane && updateLane === currentEntangledLane && (didReadFromEntangledAsyncAction = true);
              null !== current && (current = current.next = {
                lane: 0,
                tag: pendingQueue.tag,
                payload: pendingQueue.payload,
                callback: null,
                next: null
              });
              a: {
                var workInProgress2 = workInProgress$jscomp$0, update = pendingQueue;
                updateLane = props;
                var instance = instance$jscomp$0;
                switch (update.tag) {
                  case 1:
                    workInProgress2 = update.payload;
                    if ("function" === typeof workInProgress2) {
                      newState = workInProgress2.call(instance, newState, updateLane);
                      break a;
                    }
                    newState = workInProgress2;
                    break a;
                  case 3:
                    workInProgress2.flags = workInProgress2.flags & -65537 | 128;
                  case 0:
                    workInProgress2 = update.payload;
                    updateLane = "function" === typeof workInProgress2 ? workInProgress2.call(instance, newState, updateLane) : workInProgress2;
                    if (null === updateLane || void 0 === updateLane) break a;
                    newState = assign({}, newState, updateLane);
                    break a;
                  case 2:
                    hasForceUpdate = true;
                }
              }
              updateLane = pendingQueue.callback;
              null !== updateLane && (workInProgress$jscomp$0.flags |= 64, isHiddenUpdate && (workInProgress$jscomp$0.flags |= 8192), isHiddenUpdate = queue.callbacks, null === isHiddenUpdate ? queue.callbacks = [updateLane] : isHiddenUpdate.push(updateLane));
            } else
              isHiddenUpdate = {
                lane: updateLane,
                tag: pendingQueue.tag,
                payload: pendingQueue.payload,
                callback: pendingQueue.callback,
                next: null
              }, null === current ? (firstPendingUpdate = current = isHiddenUpdate, lastPendingUpdate = newState) : current = current.next = isHiddenUpdate, lastBaseUpdate |= updateLane;
            pendingQueue = pendingQueue.next;
            if (null === pendingQueue)
              if (pendingQueue = queue.shared.pending, null === pendingQueue)
                break;
              else
                isHiddenUpdate = pendingQueue, pendingQueue = isHiddenUpdate.next, isHiddenUpdate.next = null, queue.lastBaseUpdate = isHiddenUpdate, queue.shared.pending = null;
          } while (1);
          null === current && (lastPendingUpdate = newState);
          queue.baseState = lastPendingUpdate;
          queue.firstBaseUpdate = firstPendingUpdate;
          queue.lastBaseUpdate = current;
          null === firstBaseUpdate && (queue.shared.lanes = 0);
          workInProgressRootSkippedLanes |= lastBaseUpdate;
          workInProgress$jscomp$0.lanes = lastBaseUpdate;
          workInProgress$jscomp$0.memoizedState = newState;
        }
      }
      function callCallback(callback, context) {
        if ("function" !== typeof callback)
          throw Error(formatProdErrorMessage(191, callback));
        callback.call(context);
      }
      function commitCallbacks(updateQueue, context) {
        var callbacks = updateQueue.callbacks;
        if (null !== callbacks)
          for (updateQueue.callbacks = null, updateQueue = 0; updateQueue < callbacks.length; updateQueue++)
            callCallback(callbacks[updateQueue], context);
      }
      var currentTreeHiddenStackCursor = createCursor(null);
      var prevEntangledRenderLanesCursor = createCursor(0);
      function pushHiddenContext(fiber, context) {
        fiber = entangledRenderLanes;
        push(prevEntangledRenderLanesCursor, fiber);
        push(currentTreeHiddenStackCursor, context);
        entangledRenderLanes = fiber | context.baseLanes;
      }
      function reuseHiddenContextOnStack() {
        push(prevEntangledRenderLanesCursor, entangledRenderLanes);
        push(currentTreeHiddenStackCursor, currentTreeHiddenStackCursor.current);
      }
      function popHiddenContext() {
        entangledRenderLanes = prevEntangledRenderLanesCursor.current;
        pop(currentTreeHiddenStackCursor);
        pop(prevEntangledRenderLanesCursor);
      }
      var suspenseHandlerStackCursor = createCursor(null);
      var shellBoundary = null;
      function pushPrimaryTreeSuspenseHandler(handler) {
        var current = handler.alternate;
        push(suspenseStackCursor, suspenseStackCursor.current & 1);
        push(suspenseHandlerStackCursor, handler);
        null === shellBoundary && (null === current || null !== currentTreeHiddenStackCursor.current ? shellBoundary = handler : null !== current.memoizedState && (shellBoundary = handler));
      }
      function pushDehydratedActivitySuspenseHandler(fiber) {
        push(suspenseStackCursor, suspenseStackCursor.current);
        push(suspenseHandlerStackCursor, fiber);
        null === shellBoundary && (shellBoundary = fiber);
      }
      function pushOffscreenSuspenseHandler(fiber) {
        22 === fiber.tag ? (push(suspenseStackCursor, suspenseStackCursor.current), push(suspenseHandlerStackCursor, fiber), null === shellBoundary && (shellBoundary = fiber)) : reuseSuspenseHandlerOnStack(fiber);
      }
      function reuseSuspenseHandlerOnStack() {
        push(suspenseStackCursor, suspenseStackCursor.current);
        push(suspenseHandlerStackCursor, suspenseHandlerStackCursor.current);
      }
      function popSuspenseHandler(fiber) {
        pop(suspenseHandlerStackCursor);
        shellBoundary === fiber && (shellBoundary = null);
        pop(suspenseStackCursor);
      }
      var suspenseStackCursor = createCursor(0);
      function findFirstSuspended(row) {
        for (var node = row; null !== node; ) {
          if (13 === node.tag) {
            var state = node.memoizedState;
            if (null !== state && (state = state.dehydrated, null === state || isSuspenseInstancePending(state) || isSuspenseInstanceFallback(state)))
              return node;
          } else if (19 === node.tag && ("forwards" === node.memoizedProps.revealOrder || "backwards" === node.memoizedProps.revealOrder || "unstable_legacy-backwards" === node.memoizedProps.revealOrder || "together" === node.memoizedProps.revealOrder)) {
            if (0 !== (node.flags & 128)) return node;
          } else if (null !== node.child) {
            node.child.return = node;
            node = node.child;
            continue;
          }
          if (node === row) break;
          for (; null === node.sibling; ) {
            if (null === node.return || node.return === row) return null;
            node = node.return;
          }
          node.sibling.return = node.return;
          node = node.sibling;
        }
        return null;
      }
      var renderLanes = 0;
      var currentlyRenderingFiber = null;
      var currentHook = null;
      var workInProgressHook = null;
      var didScheduleRenderPhaseUpdate = false;
      var didScheduleRenderPhaseUpdateDuringThisPass = false;
      var shouldDoubleInvokeUserFnsInHooksDEV = false;
      var localIdCounter = 0;
      var thenableIndexCounter = 0;
      var thenableState = null;
      var globalClientIdCounter = 0;
      function throwInvalidHookError() {
        throw Error(formatProdErrorMessage(321));
      }
      function areHookInputsEqual(nextDeps, prevDeps) {
        if (null === prevDeps) return false;
        for (var i = 0; i < prevDeps.length && i < nextDeps.length; i++)
          if (!objectIs(nextDeps[i], prevDeps[i])) return false;
        return true;
      }
      function renderWithHooks(current, workInProgress2, Component, props, secondArg, nextRenderLanes) {
        renderLanes = nextRenderLanes;
        currentlyRenderingFiber = workInProgress2;
        workInProgress2.memoizedState = null;
        workInProgress2.updateQueue = null;
        workInProgress2.lanes = 0;
        ReactSharedInternals.H = null === current || null === current.memoizedState ? HooksDispatcherOnMount : HooksDispatcherOnUpdate;
        shouldDoubleInvokeUserFnsInHooksDEV = false;
        nextRenderLanes = Component(props, secondArg);
        shouldDoubleInvokeUserFnsInHooksDEV = false;
        didScheduleRenderPhaseUpdateDuringThisPass && (nextRenderLanes = renderWithHooksAgain(
          workInProgress2,
          Component,
          props,
          secondArg
        ));
        finishRenderingHooks(current);
        return nextRenderLanes;
      }
      function finishRenderingHooks(current) {
        ReactSharedInternals.H = ContextOnlyDispatcher;
        var didRenderTooFewHooks = null !== currentHook && null !== currentHook.next;
        renderLanes = 0;
        workInProgressHook = currentHook = currentlyRenderingFiber = null;
        didScheduleRenderPhaseUpdate = false;
        thenableIndexCounter = 0;
        thenableState = null;
        if (didRenderTooFewHooks) throw Error(formatProdErrorMessage(300));
        null === current || didReceiveUpdate || (current = current.dependencies, null !== current && checkIfContextChanged(current) && (didReceiveUpdate = true));
      }
      function renderWithHooksAgain(workInProgress2, Component, props, secondArg) {
        currentlyRenderingFiber = workInProgress2;
        var numberOfReRenders = 0;
        do {
          didScheduleRenderPhaseUpdateDuringThisPass && (thenableState = null);
          thenableIndexCounter = 0;
          didScheduleRenderPhaseUpdateDuringThisPass = false;
          if (25 <= numberOfReRenders) throw Error(formatProdErrorMessage(301));
          numberOfReRenders += 1;
          workInProgressHook = currentHook = null;
          if (null != workInProgress2.updateQueue) {
            var children = workInProgress2.updateQueue;
            children.lastEffect = null;
            children.events = null;
            children.stores = null;
            null != children.memoCache && (children.memoCache.index = 0);
          }
          ReactSharedInternals.H = HooksDispatcherOnRerender;
          children = Component(props, secondArg);
        } while (didScheduleRenderPhaseUpdateDuringThisPass);
        return children;
      }
      function TransitionAwareHostComponent() {
        var dispatcher = ReactSharedInternals.H, maybeThenable = dispatcher.useState()[0];
        maybeThenable = "function" === typeof maybeThenable.then ? useThenable(maybeThenable) : maybeThenable;
        dispatcher = dispatcher.useState()[0];
        (null !== currentHook ? currentHook.memoizedState : null) !== dispatcher && (currentlyRenderingFiber.flags |= 1024);
        return maybeThenable;
      }
      function checkDidRenderIdHook() {
        var didRenderIdHook = 0 !== localIdCounter;
        localIdCounter = 0;
        return didRenderIdHook;
      }
      function bailoutHooks(current, workInProgress2, lanes) {
        workInProgress2.updateQueue = current.updateQueue;
        workInProgress2.flags &= -2053;
        current.lanes &= ~lanes;
      }
      function resetHooksOnUnwind(workInProgress2) {
        if (didScheduleRenderPhaseUpdate) {
          for (workInProgress2 = workInProgress2.memoizedState; null !== workInProgress2; ) {
            var queue = workInProgress2.queue;
            null !== queue && (queue.pending = null);
            workInProgress2 = workInProgress2.next;
          }
          didScheduleRenderPhaseUpdate = false;
        }
        renderLanes = 0;
        workInProgressHook = currentHook = currentlyRenderingFiber = null;
        didScheduleRenderPhaseUpdateDuringThisPass = false;
        thenableIndexCounter = localIdCounter = 0;
        thenableState = null;
      }
      function mountWorkInProgressHook() {
        var hook = {
          memoizedState: null,
          baseState: null,
          baseQueue: null,
          queue: null,
          next: null
        };
        null === workInProgressHook ? currentlyRenderingFiber.memoizedState = workInProgressHook = hook : workInProgressHook = workInProgressHook.next = hook;
        return workInProgressHook;
      }
      function updateWorkInProgressHook() {
        if (null === currentHook) {
          var nextCurrentHook = currentlyRenderingFiber.alternate;
          nextCurrentHook = null !== nextCurrentHook ? nextCurrentHook.memoizedState : null;
        } else nextCurrentHook = currentHook.next;
        var nextWorkInProgressHook = null === workInProgressHook ? currentlyRenderingFiber.memoizedState : workInProgressHook.next;
        if (null !== nextWorkInProgressHook)
          workInProgressHook = nextWorkInProgressHook, currentHook = nextCurrentHook;
        else {
          if (null === nextCurrentHook) {
            if (null === currentlyRenderingFiber.alternate)
              throw Error(formatProdErrorMessage(467));
            throw Error(formatProdErrorMessage(310));
          }
          currentHook = nextCurrentHook;
          nextCurrentHook = {
            memoizedState: currentHook.memoizedState,
            baseState: currentHook.baseState,
            baseQueue: currentHook.baseQueue,
            queue: currentHook.queue,
            next: null
          };
          null === workInProgressHook ? currentlyRenderingFiber.memoizedState = workInProgressHook = nextCurrentHook : workInProgressHook = workInProgressHook.next = nextCurrentHook;
        }
        return workInProgressHook;
      }
      function createFunctionComponentUpdateQueue() {
        return { lastEffect: null, events: null, stores: null, memoCache: null };
      }
      function useThenable(thenable) {
        var index2 = thenableIndexCounter;
        thenableIndexCounter += 1;
        null === thenableState && (thenableState = []);
        thenable = trackUsedThenable(thenableState, thenable, index2);
        index2 = currentlyRenderingFiber;
        null === (null === workInProgressHook ? index2.memoizedState : workInProgressHook.next) && (index2 = index2.alternate, ReactSharedInternals.H = null === index2 || null === index2.memoizedState ? HooksDispatcherOnMount : HooksDispatcherOnUpdate);
        return thenable;
      }
      function use(usable) {
        if (null !== usable && "object" === typeof usable) {
          if ("function" === typeof usable.then) return useThenable(usable);
          if (usable.$$typeof === REACT_CONTEXT_TYPE) return readContext(usable);
        }
        throw Error(formatProdErrorMessage(438, String(usable)));
      }
      function useMemoCache(size) {
        var memoCache = null, updateQueue = currentlyRenderingFiber.updateQueue;
        null !== updateQueue && (memoCache = updateQueue.memoCache);
        if (null == memoCache) {
          var current = currentlyRenderingFiber.alternate;
          null !== current && (current = current.updateQueue, null !== current && (current = current.memoCache, null != current && (memoCache = {
            data: current.data.map(function(array) {
              return array.slice();
            }),
            index: 0
          })));
        }
        null == memoCache && (memoCache = { data: [], index: 0 });
        null === updateQueue && (updateQueue = createFunctionComponentUpdateQueue(), currentlyRenderingFiber.updateQueue = updateQueue);
        updateQueue.memoCache = memoCache;
        updateQueue = memoCache.data[memoCache.index];
        if (void 0 === updateQueue)
          for (updateQueue = memoCache.data[memoCache.index] = Array(size), current = 0; current < size; current++)
            updateQueue[current] = REACT_MEMO_CACHE_SENTINEL;
        memoCache.index++;
        return updateQueue;
      }
      function basicStateReducer(state, action) {
        return "function" === typeof action ? action(state) : action;
      }
      function updateReducer(reducer) {
        var hook = updateWorkInProgressHook();
        return updateReducerImpl(hook, currentHook, reducer);
      }
      function updateReducerImpl(hook, current, reducer) {
        var queue = hook.queue;
        if (null === queue) throw Error(formatProdErrorMessage(311));
        queue.lastRenderedReducer = reducer;
        var baseQueue = hook.baseQueue, pendingQueue = queue.pending;
        if (null !== pendingQueue) {
          if (null !== baseQueue) {
            var baseFirst = baseQueue.next;
            baseQueue.next = pendingQueue.next;
            pendingQueue.next = baseFirst;
          }
          current.baseQueue = baseQueue = pendingQueue;
          queue.pending = null;
        }
        pendingQueue = hook.baseState;
        if (null === baseQueue) hook.memoizedState = pendingQueue;
        else {
          current = baseQueue.next;
          var newBaseQueueFirst = baseFirst = null, newBaseQueueLast = null, update = current, didReadFromEntangledAsyncAction$60 = false;
          do {
            var updateLane = update.lane & -536870913;
            if (updateLane !== update.lane ? (workInProgressRootRenderLanes & updateLane) === updateLane : (renderLanes & updateLane) === updateLane) {
              var revertLane = update.revertLane;
              if (0 === revertLane)
                null !== newBaseQueueLast && (newBaseQueueLast = newBaseQueueLast.next = {
                  lane: 0,
                  revertLane: 0,
                  gesture: null,
                  action: update.action,
                  hasEagerState: update.hasEagerState,
                  eagerState: update.eagerState,
                  next: null
                }), updateLane === currentEntangledLane && (didReadFromEntangledAsyncAction$60 = true);
              else if ((renderLanes & revertLane) === revertLane) {
                update = update.next;
                revertLane === currentEntangledLane && (didReadFromEntangledAsyncAction$60 = true);
                continue;
              } else
                updateLane = {
                  lane: 0,
                  revertLane: update.revertLane,
                  gesture: null,
                  action: update.action,
                  hasEagerState: update.hasEagerState,
                  eagerState: update.eagerState,
                  next: null
                }, null === newBaseQueueLast ? (newBaseQueueFirst = newBaseQueueLast = updateLane, baseFirst = pendingQueue) : newBaseQueueLast = newBaseQueueLast.next = updateLane, currentlyRenderingFiber.lanes |= revertLane, workInProgressRootSkippedLanes |= revertLane;
              updateLane = update.action;
              shouldDoubleInvokeUserFnsInHooksDEV && reducer(pendingQueue, updateLane);
              pendingQueue = update.hasEagerState ? update.eagerState : reducer(pendingQueue, updateLane);
            } else
              revertLane = {
                lane: updateLane,
                revertLane: update.revertLane,
                gesture: update.gesture,
                action: update.action,
                hasEagerState: update.hasEagerState,
                eagerState: update.eagerState,
                next: null
              }, null === newBaseQueueLast ? (newBaseQueueFirst = newBaseQueueLast = revertLane, baseFirst = pendingQueue) : newBaseQueueLast = newBaseQueueLast.next = revertLane, currentlyRenderingFiber.lanes |= updateLane, workInProgressRootSkippedLanes |= updateLane;
            update = update.next;
          } while (null !== update && update !== current);
          null === newBaseQueueLast ? baseFirst = pendingQueue : newBaseQueueLast.next = newBaseQueueFirst;
          if (!objectIs(pendingQueue, hook.memoizedState) && (didReceiveUpdate = true, didReadFromEntangledAsyncAction$60 && (reducer = currentEntangledActionThenable, null !== reducer)))
            throw reducer;
          hook.memoizedState = pendingQueue;
          hook.baseState = baseFirst;
          hook.baseQueue = newBaseQueueLast;
          queue.lastRenderedState = pendingQueue;
        }
        null === baseQueue && (queue.lanes = 0);
        return [hook.memoizedState, queue.dispatch];
      }
      function rerenderReducer(reducer) {
        var hook = updateWorkInProgressHook(), queue = hook.queue;
        if (null === queue) throw Error(formatProdErrorMessage(311));
        queue.lastRenderedReducer = reducer;
        var dispatch = queue.dispatch, lastRenderPhaseUpdate = queue.pending, newState = hook.memoizedState;
        if (null !== lastRenderPhaseUpdate) {
          queue.pending = null;
          var update = lastRenderPhaseUpdate = lastRenderPhaseUpdate.next;
          do
            newState = reducer(newState, update.action), update = update.next;
          while (update !== lastRenderPhaseUpdate);
          objectIs(newState, hook.memoizedState) || (didReceiveUpdate = true);
          hook.memoizedState = newState;
          null === hook.baseQueue && (hook.baseState = newState);
          queue.lastRenderedState = newState;
        }
        return [newState, dispatch];
      }
      function updateSyncExternalStore(subscribe, getSnapshot, getServerSnapshot) {
        var fiber = currentlyRenderingFiber, hook = updateWorkInProgressHook(), isHydrating$jscomp$0 = isHydrating;
        if (isHydrating$jscomp$0) {
          if (void 0 === getServerSnapshot) throw Error(formatProdErrorMessage(407));
          getServerSnapshot = getServerSnapshot();
        } else getServerSnapshot = getSnapshot();
        var snapshotChanged = !objectIs(
          (currentHook || hook).memoizedState,
          getServerSnapshot
        );
        snapshotChanged && (hook.memoizedState = getServerSnapshot, didReceiveUpdate = true);
        hook = hook.queue;
        updateEffect(subscribeToStore.bind(null, fiber, hook, subscribe), [
          subscribe
        ]);
        if (hook.getSnapshot !== getSnapshot || snapshotChanged || null !== workInProgressHook && workInProgressHook.memoizedState.tag & 1) {
          fiber.flags |= 2048;
          pushSimpleEffect(
            9,
            { destroy: void 0 },
            updateStoreInstance.bind(
              null,
              fiber,
              hook,
              getServerSnapshot,
              getSnapshot
            ),
            null
          );
          if (null === workInProgressRoot) throw Error(formatProdErrorMessage(349));
          isHydrating$jscomp$0 || 0 !== (renderLanes & 127) || pushStoreConsistencyCheck(fiber, getSnapshot, getServerSnapshot);
        }
        return getServerSnapshot;
      }
      function pushStoreConsistencyCheck(fiber, getSnapshot, renderedSnapshot) {
        fiber.flags |= 16384;
        fiber = { getSnapshot, value: renderedSnapshot };
        getSnapshot = currentlyRenderingFiber.updateQueue;
        null === getSnapshot ? (getSnapshot = createFunctionComponentUpdateQueue(), currentlyRenderingFiber.updateQueue = getSnapshot, getSnapshot.stores = [fiber]) : (renderedSnapshot = getSnapshot.stores, null === renderedSnapshot ? getSnapshot.stores = [fiber] : renderedSnapshot.push(fiber));
      }
      function updateStoreInstance(fiber, inst, nextSnapshot, getSnapshot) {
        inst.value = nextSnapshot;
        inst.getSnapshot = getSnapshot;
        checkIfSnapshotChanged(inst) && forceStoreRerender(fiber);
      }
      function subscribeToStore(fiber, inst, subscribe) {
        return subscribe(function() {
          checkIfSnapshotChanged(inst) && forceStoreRerender(fiber);
        });
      }
      function checkIfSnapshotChanged(inst) {
        var latestGetSnapshot = inst.getSnapshot;
        inst = inst.value;
        try {
          var nextValue = latestGetSnapshot();
          return !objectIs(inst, nextValue);
        } catch (error) {
          return true;
        }
      }
      function forceStoreRerender(fiber) {
        var root2 = enqueueConcurrentRenderForLane(fiber, 2);
        null !== root2 && scheduleUpdateOnFiber(root2, fiber, 2);
      }
      function mountStateImpl(initialState) {
        var hook = mountWorkInProgressHook();
        if ("function" === typeof initialState) {
          var initialStateInitializer = initialState;
          initialState = initialStateInitializer();
          if (shouldDoubleInvokeUserFnsInHooksDEV) {
            setIsStrictModeForDevtools(true);
            try {
              initialStateInitializer();
            } finally {
              setIsStrictModeForDevtools(false);
            }
          }
        }
        hook.memoizedState = hook.baseState = initialState;
        hook.queue = {
          pending: null,
          lanes: 0,
          dispatch: null,
          lastRenderedReducer: basicStateReducer,
          lastRenderedState: initialState
        };
        return hook;
      }
      function updateOptimisticImpl(hook, current, passthrough, reducer) {
        hook.baseState = passthrough;
        return updateReducerImpl(
          hook,
          currentHook,
          "function" === typeof reducer ? reducer : basicStateReducer
        );
      }
      function dispatchActionState(fiber, actionQueue, setPendingState, setState, payload) {
        if (isRenderPhaseUpdate(fiber)) throw Error(formatProdErrorMessage(485));
        fiber = actionQueue.action;
        if (null !== fiber) {
          var actionNode = {
            payload,
            action: fiber,
            next: null,
            isTransition: true,
            status: "pending",
            value: null,
            reason: null,
            listeners: [],
            then: function(listener) {
              actionNode.listeners.push(listener);
            }
          };
          null !== ReactSharedInternals.T ? setPendingState(true) : actionNode.isTransition = false;
          setState(actionNode);
          setPendingState = actionQueue.pending;
          null === setPendingState ? (actionNode.next = actionQueue.pending = actionNode, runActionStateAction(actionQueue, actionNode)) : (actionNode.next = setPendingState.next, actionQueue.pending = setPendingState.next = actionNode);
        }
      }
      function runActionStateAction(actionQueue, node) {
        var action = node.action, payload = node.payload, prevState = actionQueue.state;
        if (node.isTransition) {
          var prevTransition = ReactSharedInternals.T, currentTransition = {};
          ReactSharedInternals.T = currentTransition;
          try {
            var returnValue = action(prevState, payload), onStartTransitionFinish = ReactSharedInternals.S;
            null !== onStartTransitionFinish && onStartTransitionFinish(currentTransition, returnValue);
            handleActionReturnValue(actionQueue, node, returnValue);
          } catch (error) {
            onActionError(actionQueue, node, error);
          } finally {
            null !== prevTransition && null !== currentTransition.types && (prevTransition.types = currentTransition.types), ReactSharedInternals.T = prevTransition;
          }
        } else
          try {
            prevTransition = action(prevState, payload), handleActionReturnValue(actionQueue, node, prevTransition);
          } catch (error$66) {
            onActionError(actionQueue, node, error$66);
          }
      }
      function handleActionReturnValue(actionQueue, node, returnValue) {
        null !== returnValue && "object" === typeof returnValue && "function" === typeof returnValue.then ? returnValue.then(
          function(nextState) {
            onActionSuccess(actionQueue, node, nextState);
          },
          function(error) {
            return onActionError(actionQueue, node, error);
          }
        ) : onActionSuccess(actionQueue, node, returnValue);
      }
      function onActionSuccess(actionQueue, actionNode, nextState) {
        actionNode.status = "fulfilled";
        actionNode.value = nextState;
        notifyActionListeners(actionNode);
        actionQueue.state = nextState;
        actionNode = actionQueue.pending;
        null !== actionNode && (nextState = actionNode.next, nextState === actionNode ? actionQueue.pending = null : (nextState = nextState.next, actionNode.next = nextState, runActionStateAction(actionQueue, nextState)));
      }
      function onActionError(actionQueue, actionNode, error) {
        var last = actionQueue.pending;
        actionQueue.pending = null;
        if (null !== last) {
          last = last.next;
          do
            actionNode.status = "rejected", actionNode.reason = error, notifyActionListeners(actionNode), actionNode = actionNode.next;
          while (actionNode !== last);
        }
        actionQueue.action = null;
      }
      function notifyActionListeners(actionNode) {
        actionNode = actionNode.listeners;
        for (var i = 0; i < actionNode.length; i++) (0, actionNode[i])();
      }
      function actionStateReducer(oldState, newState) {
        return newState;
      }
      function mountActionState(action, initialStateProp) {
        if (isHydrating) {
          var ssrFormState = workInProgressRoot.formState;
          if (null !== ssrFormState) {
            a: {
              var JSCompiler_inline_result = currentlyRenderingFiber;
              if (isHydrating) {
                if (nextHydratableInstance) {
                  b: {
                    var JSCompiler_inline_result$jscomp$0 = nextHydratableInstance;
                    for (var inRootOrSingleton = rootOrSingletonContext; 8 !== JSCompiler_inline_result$jscomp$0.nodeType; ) {
                      if (!inRootOrSingleton) {
                        JSCompiler_inline_result$jscomp$0 = null;
                        break b;
                      }
                      JSCompiler_inline_result$jscomp$0 = getNextHydratable(
                        JSCompiler_inline_result$jscomp$0.nextSibling
                      );
                      if (null === JSCompiler_inline_result$jscomp$0) {
                        JSCompiler_inline_result$jscomp$0 = null;
                        break b;
                      }
                    }
                    inRootOrSingleton = JSCompiler_inline_result$jscomp$0.data;
                    JSCompiler_inline_result$jscomp$0 = "F!" === inRootOrSingleton || "F" === inRootOrSingleton ? JSCompiler_inline_result$jscomp$0 : null;
                  }
                  if (JSCompiler_inline_result$jscomp$0) {
                    nextHydratableInstance = getNextHydratable(
                      JSCompiler_inline_result$jscomp$0.nextSibling
                    );
                    JSCompiler_inline_result = "F!" === JSCompiler_inline_result$jscomp$0.data;
                    break a;
                  }
                }
                throwOnHydrationMismatch(JSCompiler_inline_result);
              }
              JSCompiler_inline_result = false;
            }
            JSCompiler_inline_result && (initialStateProp = ssrFormState[0]);
          }
        }
        ssrFormState = mountWorkInProgressHook();
        ssrFormState.memoizedState = ssrFormState.baseState = initialStateProp;
        JSCompiler_inline_result = {
          pending: null,
          lanes: 0,
          dispatch: null,
          lastRenderedReducer: actionStateReducer,
          lastRenderedState: initialStateProp
        };
        ssrFormState.queue = JSCompiler_inline_result;
        ssrFormState = dispatchSetState.bind(
          null,
          currentlyRenderingFiber,
          JSCompiler_inline_result
        );
        JSCompiler_inline_result.dispatch = ssrFormState;
        JSCompiler_inline_result = mountStateImpl(false);
        inRootOrSingleton = dispatchOptimisticSetState.bind(
          null,
          currentlyRenderingFiber,
          false,
          JSCompiler_inline_result.queue
        );
        JSCompiler_inline_result = mountWorkInProgressHook();
        JSCompiler_inline_result$jscomp$0 = {
          state: initialStateProp,
          dispatch: null,
          action,
          pending: null
        };
        JSCompiler_inline_result.queue = JSCompiler_inline_result$jscomp$0;
        ssrFormState = dispatchActionState.bind(
          null,
          currentlyRenderingFiber,
          JSCompiler_inline_result$jscomp$0,
          inRootOrSingleton,
          ssrFormState
        );
        JSCompiler_inline_result$jscomp$0.dispatch = ssrFormState;
        JSCompiler_inline_result.memoizedState = action;
        return [initialStateProp, ssrFormState, false];
      }
      function updateActionState(action) {
        var stateHook = updateWorkInProgressHook();
        return updateActionStateImpl(stateHook, currentHook, action);
      }
      function updateActionStateImpl(stateHook, currentStateHook, action) {
        currentStateHook = updateReducerImpl(
          stateHook,
          currentStateHook,
          actionStateReducer
        )[0];
        stateHook = updateReducer(basicStateReducer)[0];
        if ("object" === typeof currentStateHook && null !== currentStateHook && "function" === typeof currentStateHook.then)
          try {
            var state = useThenable(currentStateHook);
          } catch (x) {
            if (x === SuspenseException) throw SuspenseActionException;
            throw x;
          }
        else state = currentStateHook;
        currentStateHook = updateWorkInProgressHook();
        var actionQueue = currentStateHook.queue, dispatch = actionQueue.dispatch;
        action !== currentStateHook.memoizedState && (currentlyRenderingFiber.flags |= 2048, pushSimpleEffect(
          9,
          { destroy: void 0 },
          actionStateActionEffect.bind(null, actionQueue, action),
          null
        ));
        return [state, dispatch, stateHook];
      }
      function actionStateActionEffect(actionQueue, action) {
        actionQueue.action = action;
      }
      function rerenderActionState(action) {
        var stateHook = updateWorkInProgressHook(), currentStateHook = currentHook;
        if (null !== currentStateHook)
          return updateActionStateImpl(stateHook, currentStateHook, action);
        updateWorkInProgressHook();
        stateHook = stateHook.memoizedState;
        currentStateHook = updateWorkInProgressHook();
        var dispatch = currentStateHook.queue.dispatch;
        currentStateHook.memoizedState = action;
        return [stateHook, dispatch, false];
      }
      function pushSimpleEffect(tag, inst, create, deps) {
        tag = { tag, create, deps, inst, next: null };
        inst = currentlyRenderingFiber.updateQueue;
        null === inst && (inst = createFunctionComponentUpdateQueue(), currentlyRenderingFiber.updateQueue = inst);
        create = inst.lastEffect;
        null === create ? inst.lastEffect = tag.next = tag : (deps = create.next, create.next = tag, tag.next = deps, inst.lastEffect = tag);
        return tag;
      }
      function updateRef() {
        return updateWorkInProgressHook().memoizedState;
      }
      function mountEffectImpl(fiberFlags, hookFlags, create, deps) {
        var hook = mountWorkInProgressHook();
        currentlyRenderingFiber.flags |= fiberFlags;
        hook.memoizedState = pushSimpleEffect(
          1 | hookFlags,
          { destroy: void 0 },
          create,
          void 0 === deps ? null : deps
        );
      }
      function updateEffectImpl(fiberFlags, hookFlags, create, deps) {
        var hook = updateWorkInProgressHook();
        deps = void 0 === deps ? null : deps;
        var inst = hook.memoizedState.inst;
        null !== currentHook && null !== deps && areHookInputsEqual(deps, currentHook.memoizedState.deps) ? hook.memoizedState = pushSimpleEffect(hookFlags, inst, create, deps) : (currentlyRenderingFiber.flags |= fiberFlags, hook.memoizedState = pushSimpleEffect(
          1 | hookFlags,
          inst,
          create,
          deps
        ));
      }
      function mountEffect(create, deps) {
        mountEffectImpl(8390656, 8, create, deps);
      }
      function updateEffect(create, deps) {
        updateEffectImpl(2048, 8, create, deps);
      }
      function useEffectEventImpl(payload) {
        currentlyRenderingFiber.flags |= 4;
        var componentUpdateQueue = currentlyRenderingFiber.updateQueue;
        if (null === componentUpdateQueue)
          componentUpdateQueue = createFunctionComponentUpdateQueue(), currentlyRenderingFiber.updateQueue = componentUpdateQueue, componentUpdateQueue.events = [payload];
        else {
          var events = componentUpdateQueue.events;
          null === events ? componentUpdateQueue.events = [payload] : events.push(payload);
        }
      }
      function updateEvent(callback) {
        var ref = updateWorkInProgressHook().memoizedState;
        useEffectEventImpl({ ref, nextImpl: callback });
        return function() {
          if (0 !== (executionContext & 2)) throw Error(formatProdErrorMessage(440));
          return ref.impl.apply(void 0, arguments);
        };
      }
      function updateInsertionEffect(create, deps) {
        return updateEffectImpl(4, 2, create, deps);
      }
      function updateLayoutEffect(create, deps) {
        return updateEffectImpl(4, 4, create, deps);
      }
      function imperativeHandleEffect(create, ref) {
        if ("function" === typeof ref) {
          create = create();
          var refCleanup = ref(create);
          return function() {
            "function" === typeof refCleanup ? refCleanup() : ref(null);
          };
        }
        if (null !== ref && void 0 !== ref)
          return create = create(), ref.current = create, function() {
            ref.current = null;
          };
      }
      function updateImperativeHandle(ref, create, deps) {
        deps = null !== deps && void 0 !== deps ? deps.concat([ref]) : null;
        updateEffectImpl(4, 4, imperativeHandleEffect.bind(null, create, ref), deps);
      }
      function mountDebugValue() {
      }
      function updateCallback(callback, deps) {
        var hook = updateWorkInProgressHook();
        deps = void 0 === deps ? null : deps;
        var prevState = hook.memoizedState;
        if (null !== deps && areHookInputsEqual(deps, prevState[1]))
          return prevState[0];
        hook.memoizedState = [callback, deps];
        return callback;
      }
      function updateMemo(nextCreate, deps) {
        var hook = updateWorkInProgressHook();
        deps = void 0 === deps ? null : deps;
        var prevState = hook.memoizedState;
        if (null !== deps && areHookInputsEqual(deps, prevState[1]))
          return prevState[0];
        prevState = nextCreate();
        if (shouldDoubleInvokeUserFnsInHooksDEV) {
          setIsStrictModeForDevtools(true);
          try {
            nextCreate();
          } finally {
            setIsStrictModeForDevtools(false);
          }
        }
        hook.memoizedState = [prevState, deps];
        return prevState;
      }
      function mountDeferredValueImpl(hook, value, initialValue) {
        if (void 0 === initialValue || 0 !== (renderLanes & 1073741824) && 0 === (workInProgressRootRenderLanes & 261930))
          return hook.memoizedState = value;
        hook.memoizedState = initialValue;
        hook = requestDeferredLane();
        currentlyRenderingFiber.lanes |= hook;
        workInProgressRootSkippedLanes |= hook;
        return initialValue;
      }
      function updateDeferredValueImpl(hook, prevValue, value, initialValue) {
        if (objectIs(value, prevValue)) return value;
        if (null !== currentTreeHiddenStackCursor.current)
          return hook = mountDeferredValueImpl(hook, value, initialValue), objectIs(hook, prevValue) || (didReceiveUpdate = true), hook;
        if (0 === (renderLanes & 42) || 0 !== (renderLanes & 1073741824) && 0 === (workInProgressRootRenderLanes & 261930))
          return didReceiveUpdate = true, hook.memoizedState = value;
        hook = requestDeferredLane();
        currentlyRenderingFiber.lanes |= hook;
        workInProgressRootSkippedLanes |= hook;
        return prevValue;
      }
      function startTransition(fiber, queue, pendingState, finishedState, callback) {
        var previousPriority = ReactDOMSharedInternals.p;
        ReactDOMSharedInternals.p = 0 !== previousPriority && 8 > previousPriority ? previousPriority : 8;
        var prevTransition = ReactSharedInternals.T, currentTransition = {};
        ReactSharedInternals.T = currentTransition;
        dispatchOptimisticSetState(fiber, false, queue, pendingState);
        try {
          var returnValue = callback(), onStartTransitionFinish = ReactSharedInternals.S;
          null !== onStartTransitionFinish && onStartTransitionFinish(currentTransition, returnValue);
          if (null !== returnValue && "object" === typeof returnValue && "function" === typeof returnValue.then) {
            var thenableForFinishedState = chainThenableValue(
              returnValue,
              finishedState
            );
            dispatchSetStateInternal(
              fiber,
              queue,
              thenableForFinishedState,
              requestUpdateLane(fiber)
            );
          } else
            dispatchSetStateInternal(
              fiber,
              queue,
              finishedState,
              requestUpdateLane(fiber)
            );
        } catch (error) {
          dispatchSetStateInternal(
            fiber,
            queue,
            { then: function() {
            }, status: "rejected", reason: error },
            requestUpdateLane()
          );
        } finally {
          ReactDOMSharedInternals.p = previousPriority, null !== prevTransition && null !== currentTransition.types && (prevTransition.types = currentTransition.types), ReactSharedInternals.T = prevTransition;
        }
      }
      function noop() {
      }
      function startHostTransition(formFiber, pendingState, action, formData) {
        if (5 !== formFiber.tag) throw Error(formatProdErrorMessage(476));
        var queue = ensureFormComponentIsStateful(formFiber).queue;
        startTransition(
          formFiber,
          queue,
          pendingState,
          sharedNotPendingObject,
          null === action ? noop : function() {
            requestFormReset$1(formFiber);
            return action(formData);
          }
        );
      }
      function ensureFormComponentIsStateful(formFiber) {
        var existingStateHook = formFiber.memoizedState;
        if (null !== existingStateHook) return existingStateHook;
        existingStateHook = {
          memoizedState: sharedNotPendingObject,
          baseState: sharedNotPendingObject,
          baseQueue: null,
          queue: {
            pending: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: basicStateReducer,
            lastRenderedState: sharedNotPendingObject
          },
          next: null
        };
        var initialResetState = {};
        existingStateHook.next = {
          memoizedState: initialResetState,
          baseState: initialResetState,
          baseQueue: null,
          queue: {
            pending: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: basicStateReducer,
            lastRenderedState: initialResetState
          },
          next: null
        };
        formFiber.memoizedState = existingStateHook;
        formFiber = formFiber.alternate;
        null !== formFiber && (formFiber.memoizedState = existingStateHook);
        return existingStateHook;
      }
      function requestFormReset$1(formFiber) {
        var stateHook = ensureFormComponentIsStateful(formFiber);
        null === stateHook.next && (stateHook = formFiber.alternate.memoizedState);
        dispatchSetStateInternal(
          formFiber,
          stateHook.next.queue,
          {},
          requestUpdateLane()
        );
      }
      function useHostTransitionStatus() {
        return readContext(HostTransitionContext);
      }
      function updateId() {
        return updateWorkInProgressHook().memoizedState;
      }
      function updateRefresh() {
        return updateWorkInProgressHook().memoizedState;
      }
      function refreshCache(fiber) {
        for (var provider = fiber.return; null !== provider; ) {
          switch (provider.tag) {
            case 24:
            case 3:
              var lane = requestUpdateLane();
              fiber = createUpdate(lane);
              var root$69 = enqueueUpdate(provider, fiber, lane);
              null !== root$69 && (scheduleUpdateOnFiber(root$69, provider, lane), entangleTransitions(root$69, provider, lane));
              provider = { cache: createCache() };
              fiber.payload = provider;
              return;
          }
          provider = provider.return;
        }
      }
      function dispatchReducerAction(fiber, queue, action) {
        var lane = requestUpdateLane();
        action = {
          lane,
          revertLane: 0,
          gesture: null,
          action,
          hasEagerState: false,
          eagerState: null,
          next: null
        };
        isRenderPhaseUpdate(fiber) ? enqueueRenderPhaseUpdate(queue, action) : (action = enqueueConcurrentHookUpdate(fiber, queue, action, lane), null !== action && (scheduleUpdateOnFiber(action, fiber, lane), entangleTransitionUpdate(action, queue, lane)));
      }
      function dispatchSetState(fiber, queue, action) {
        var lane = requestUpdateLane();
        dispatchSetStateInternal(fiber, queue, action, lane);
      }
      function dispatchSetStateInternal(fiber, queue, action, lane) {
        var update = {
          lane,
          revertLane: 0,
          gesture: null,
          action,
          hasEagerState: false,
          eagerState: null,
          next: null
        };
        if (isRenderPhaseUpdate(fiber)) enqueueRenderPhaseUpdate(queue, update);
        else {
          var alternate = fiber.alternate;
          if (0 === fiber.lanes && (null === alternate || 0 === alternate.lanes) && (alternate = queue.lastRenderedReducer, null !== alternate))
            try {
              var currentState = queue.lastRenderedState, eagerState = alternate(currentState, action);
              update.hasEagerState = true;
              update.eagerState = eagerState;
              if (objectIs(eagerState, currentState))
                return enqueueUpdate$1(fiber, queue, update, 0), null === workInProgressRoot && finishQueueingConcurrentUpdates(), false;
            } catch (error) {
            } finally {
            }
          action = enqueueConcurrentHookUpdate(fiber, queue, update, lane);
          if (null !== action)
            return scheduleUpdateOnFiber(action, fiber, lane), entangleTransitionUpdate(action, queue, lane), true;
        }
        return false;
      }
      function dispatchOptimisticSetState(fiber, throwIfDuringRender, queue, action) {
        action = {
          lane: 2,
          revertLane: requestTransitionLane(),
          gesture: null,
          action,
          hasEagerState: false,
          eagerState: null,
          next: null
        };
        if (isRenderPhaseUpdate(fiber)) {
          if (throwIfDuringRender) throw Error(formatProdErrorMessage(479));
        } else
          throwIfDuringRender = enqueueConcurrentHookUpdate(
            fiber,
            queue,
            action,
            2
          ), null !== throwIfDuringRender && scheduleUpdateOnFiber(throwIfDuringRender, fiber, 2);
      }
      function isRenderPhaseUpdate(fiber) {
        var alternate = fiber.alternate;
        return fiber === currentlyRenderingFiber || null !== alternate && alternate === currentlyRenderingFiber;
      }
      function enqueueRenderPhaseUpdate(queue, update) {
        didScheduleRenderPhaseUpdateDuringThisPass = didScheduleRenderPhaseUpdate = true;
        var pending = queue.pending;
        null === pending ? update.next = update : (update.next = pending.next, pending.next = update);
        queue.pending = update;
      }
      function entangleTransitionUpdate(root2, queue, lane) {
        if (0 !== (lane & 4194048)) {
          var queueLanes = queue.lanes;
          queueLanes &= root2.pendingLanes;
          lane |= queueLanes;
          queue.lanes = lane;
          markRootEntangled(root2, lane);
        }
      }
      var ContextOnlyDispatcher = {
        readContext,
        use,
        useCallback: throwInvalidHookError,
        useContext: throwInvalidHookError,
        useEffect: throwInvalidHookError,
        useImperativeHandle: throwInvalidHookError,
        useLayoutEffect: throwInvalidHookError,
        useInsertionEffect: throwInvalidHookError,
        useMemo: throwInvalidHookError,
        useReducer: throwInvalidHookError,
        useRef: throwInvalidHookError,
        useState: throwInvalidHookError,
        useDebugValue: throwInvalidHookError,
        useDeferredValue: throwInvalidHookError,
        useTransition: throwInvalidHookError,
        useSyncExternalStore: throwInvalidHookError,
        useId: throwInvalidHookError,
        useHostTransitionStatus: throwInvalidHookError,
        useFormState: throwInvalidHookError,
        useActionState: throwInvalidHookError,
        useOptimistic: throwInvalidHookError,
        useMemoCache: throwInvalidHookError,
        useCacheRefresh: throwInvalidHookError
      };
      ContextOnlyDispatcher.useEffectEvent = throwInvalidHookError;
      var HooksDispatcherOnMount = {
        readContext,
        use,
        useCallback: function(callback, deps) {
          mountWorkInProgressHook().memoizedState = [
            callback,
            void 0 === deps ? null : deps
          ];
          return callback;
        },
        useContext: readContext,
        useEffect: mountEffect,
        useImperativeHandle: function(ref, create, deps) {
          deps = null !== deps && void 0 !== deps ? deps.concat([ref]) : null;
          mountEffectImpl(
            4194308,
            4,
            imperativeHandleEffect.bind(null, create, ref),
            deps
          );
        },
        useLayoutEffect: function(create, deps) {
          return mountEffectImpl(4194308, 4, create, deps);
        },
        useInsertionEffect: function(create, deps) {
          mountEffectImpl(4, 2, create, deps);
        },
        useMemo: function(nextCreate, deps) {
          var hook = mountWorkInProgressHook();
          deps = void 0 === deps ? null : deps;
          var nextValue = nextCreate();
          if (shouldDoubleInvokeUserFnsInHooksDEV) {
            setIsStrictModeForDevtools(true);
            try {
              nextCreate();
            } finally {
              setIsStrictModeForDevtools(false);
            }
          }
          hook.memoizedState = [nextValue, deps];
          return nextValue;
        },
        useReducer: function(reducer, initialArg, init) {
          var hook = mountWorkInProgressHook();
          if (void 0 !== init) {
            var initialState = init(initialArg);
            if (shouldDoubleInvokeUserFnsInHooksDEV) {
              setIsStrictModeForDevtools(true);
              try {
                init(initialArg);
              } finally {
                setIsStrictModeForDevtools(false);
              }
            }
          } else initialState = initialArg;
          hook.memoizedState = hook.baseState = initialState;
          reducer = {
            pending: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: reducer,
            lastRenderedState: initialState
          };
          hook.queue = reducer;
          reducer = reducer.dispatch = dispatchReducerAction.bind(
            null,
            currentlyRenderingFiber,
            reducer
          );
          return [hook.memoizedState, reducer];
        },
        useRef: function(initialValue) {
          var hook = mountWorkInProgressHook();
          initialValue = { current: initialValue };
          return hook.memoizedState = initialValue;
        },
        useState: function(initialState) {
          initialState = mountStateImpl(initialState);
          var queue = initialState.queue, dispatch = dispatchSetState.bind(null, currentlyRenderingFiber, queue);
          queue.dispatch = dispatch;
          return [initialState.memoizedState, dispatch];
        },
        useDebugValue: mountDebugValue,
        useDeferredValue: function(value, initialValue) {
          var hook = mountWorkInProgressHook();
          return mountDeferredValueImpl(hook, value, initialValue);
        },
        useTransition: function() {
          var stateHook = mountStateImpl(false);
          stateHook = startTransition.bind(
            null,
            currentlyRenderingFiber,
            stateHook.queue,
            true,
            false
          );
          mountWorkInProgressHook().memoizedState = stateHook;
          return [false, stateHook];
        },
        useSyncExternalStore: function(subscribe, getSnapshot, getServerSnapshot) {
          var fiber = currentlyRenderingFiber, hook = mountWorkInProgressHook();
          if (isHydrating) {
            if (void 0 === getServerSnapshot)
              throw Error(formatProdErrorMessage(407));
            getServerSnapshot = getServerSnapshot();
          } else {
            getServerSnapshot = getSnapshot();
            if (null === workInProgressRoot)
              throw Error(formatProdErrorMessage(349));
            0 !== (workInProgressRootRenderLanes & 127) || pushStoreConsistencyCheck(fiber, getSnapshot, getServerSnapshot);
          }
          hook.memoizedState = getServerSnapshot;
          var inst = { value: getServerSnapshot, getSnapshot };
          hook.queue = inst;
          mountEffect(subscribeToStore.bind(null, fiber, inst, subscribe), [
            subscribe
          ]);
          fiber.flags |= 2048;
          pushSimpleEffect(
            9,
            { destroy: void 0 },
            updateStoreInstance.bind(
              null,
              fiber,
              inst,
              getServerSnapshot,
              getSnapshot
            ),
            null
          );
          return getServerSnapshot;
        },
        useId: function() {
          var hook = mountWorkInProgressHook(), identifierPrefix = workInProgressRoot.identifierPrefix;
          if (isHydrating) {
            var JSCompiler_inline_result = treeContextOverflow;
            var idWithLeadingBit = treeContextId;
            JSCompiler_inline_result = (idWithLeadingBit & ~(1 << 32 - clz32(idWithLeadingBit) - 1)).toString(32) + JSCompiler_inline_result;
            identifierPrefix = "_" + identifierPrefix + "R_" + JSCompiler_inline_result;
            JSCompiler_inline_result = localIdCounter++;
            0 < JSCompiler_inline_result && (identifierPrefix += "H" + JSCompiler_inline_result.toString(32));
            identifierPrefix += "_";
          } else
            JSCompiler_inline_result = globalClientIdCounter++, identifierPrefix = "_" + identifierPrefix + "r_" + JSCompiler_inline_result.toString(32) + "_";
          return hook.memoizedState = identifierPrefix;
        },
        useHostTransitionStatus,
        useFormState: mountActionState,
        useActionState: mountActionState,
        useOptimistic: function(passthrough) {
          var hook = mountWorkInProgressHook();
          hook.memoizedState = hook.baseState = passthrough;
          var queue = {
            pending: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: null,
            lastRenderedState: null
          };
          hook.queue = queue;
          hook = dispatchOptimisticSetState.bind(
            null,
            currentlyRenderingFiber,
            true,
            queue
          );
          queue.dispatch = hook;
          return [passthrough, hook];
        },
        useMemoCache,
        useCacheRefresh: function() {
          return mountWorkInProgressHook().memoizedState = refreshCache.bind(
            null,
            currentlyRenderingFiber
          );
        },
        useEffectEvent: function(callback) {
          var hook = mountWorkInProgressHook(), ref = { impl: callback };
          hook.memoizedState = ref;
          return function() {
            if (0 !== (executionContext & 2))
              throw Error(formatProdErrorMessage(440));
            return ref.impl.apply(void 0, arguments);
          };
        }
      };
      var HooksDispatcherOnUpdate = {
        readContext,
        use,
        useCallback: updateCallback,
        useContext: readContext,
        useEffect: updateEffect,
        useImperativeHandle: updateImperativeHandle,
        useInsertionEffect: updateInsertionEffect,
        useLayoutEffect: updateLayoutEffect,
        useMemo: updateMemo,
        useReducer: updateReducer,
        useRef: updateRef,
        useState: function() {
          return updateReducer(basicStateReducer);
        },
        useDebugValue: mountDebugValue,
        useDeferredValue: function(value, initialValue) {
          var hook = updateWorkInProgressHook();
          return updateDeferredValueImpl(
            hook,
            currentHook.memoizedState,
            value,
            initialValue
          );
        },
        useTransition: function() {
          var booleanOrThenable = updateReducer(basicStateReducer)[0], start = updateWorkInProgressHook().memoizedState;
          return [
            "boolean" === typeof booleanOrThenable ? booleanOrThenable : useThenable(booleanOrThenable),
            start
          ];
        },
        useSyncExternalStore: updateSyncExternalStore,
        useId: updateId,
        useHostTransitionStatus,
        useFormState: updateActionState,
        useActionState: updateActionState,
        useOptimistic: function(passthrough, reducer) {
          var hook = updateWorkInProgressHook();
          return updateOptimisticImpl(hook, currentHook, passthrough, reducer);
        },
        useMemoCache,
        useCacheRefresh: updateRefresh
      };
      HooksDispatcherOnUpdate.useEffectEvent = updateEvent;
      var HooksDispatcherOnRerender = {
        readContext,
        use,
        useCallback: updateCallback,
        useContext: readContext,
        useEffect: updateEffect,
        useImperativeHandle: updateImperativeHandle,
        useInsertionEffect: updateInsertionEffect,
        useLayoutEffect: updateLayoutEffect,
        useMemo: updateMemo,
        useReducer: rerenderReducer,
        useRef: updateRef,
        useState: function() {
          return rerenderReducer(basicStateReducer);
        },
        useDebugValue: mountDebugValue,
        useDeferredValue: function(value, initialValue) {
          var hook = updateWorkInProgressHook();
          return null === currentHook ? mountDeferredValueImpl(hook, value, initialValue) : updateDeferredValueImpl(
            hook,
            currentHook.memoizedState,
            value,
            initialValue
          );
        },
        useTransition: function() {
          var booleanOrThenable = rerenderReducer(basicStateReducer)[0], start = updateWorkInProgressHook().memoizedState;
          return [
            "boolean" === typeof booleanOrThenable ? booleanOrThenable : useThenable(booleanOrThenable),
            start
          ];
        },
        useSyncExternalStore: updateSyncExternalStore,
        useId: updateId,
        useHostTransitionStatus,
        useFormState: rerenderActionState,
        useActionState: rerenderActionState,
        useOptimistic: function(passthrough, reducer) {
          var hook = updateWorkInProgressHook();
          if (null !== currentHook)
            return updateOptimisticImpl(hook, currentHook, passthrough, reducer);
          hook.baseState = passthrough;
          return [passthrough, hook.queue.dispatch];
        },
        useMemoCache,
        useCacheRefresh: updateRefresh
      };
      HooksDispatcherOnRerender.useEffectEvent = updateEvent;
      function applyDerivedStateFromProps(workInProgress2, ctor, getDerivedStateFromProps, nextProps) {
        ctor = workInProgress2.memoizedState;
        getDerivedStateFromProps = getDerivedStateFromProps(nextProps, ctor);
        getDerivedStateFromProps = null === getDerivedStateFromProps || void 0 === getDerivedStateFromProps ? ctor : assign({}, ctor, getDerivedStateFromProps);
        workInProgress2.memoizedState = getDerivedStateFromProps;
        0 === workInProgress2.lanes && (workInProgress2.updateQueue.baseState = getDerivedStateFromProps);
      }
      var classComponentUpdater = {
        enqueueSetState: function(inst, payload, callback) {
          inst = inst._reactInternals;
          var lane = requestUpdateLane(), update = createUpdate(lane);
          update.payload = payload;
          void 0 !== callback && null !== callback && (update.callback = callback);
          payload = enqueueUpdate(inst, update, lane);
          null !== payload && (scheduleUpdateOnFiber(payload, inst, lane), entangleTransitions(payload, inst, lane));
        },
        enqueueReplaceState: function(inst, payload, callback) {
          inst = inst._reactInternals;
          var lane = requestUpdateLane(), update = createUpdate(lane);
          update.tag = 1;
          update.payload = payload;
          void 0 !== callback && null !== callback && (update.callback = callback);
          payload = enqueueUpdate(inst, update, lane);
          null !== payload && (scheduleUpdateOnFiber(payload, inst, lane), entangleTransitions(payload, inst, lane));
        },
        enqueueForceUpdate: function(inst, callback) {
          inst = inst._reactInternals;
          var lane = requestUpdateLane(), update = createUpdate(lane);
          update.tag = 2;
          void 0 !== callback && null !== callback && (update.callback = callback);
          callback = enqueueUpdate(inst, update, lane);
          null !== callback && (scheduleUpdateOnFiber(callback, inst, lane), entangleTransitions(callback, inst, lane));
        }
      };
      function checkShouldComponentUpdate(workInProgress2, ctor, oldProps, newProps, oldState, newState, nextContext) {
        workInProgress2 = workInProgress2.stateNode;
        return "function" === typeof workInProgress2.shouldComponentUpdate ? workInProgress2.shouldComponentUpdate(newProps, newState, nextContext) : ctor.prototype && ctor.prototype.isPureReactComponent ? !shallowEqual(oldProps, newProps) || !shallowEqual(oldState, newState) : true;
      }
      function callComponentWillReceiveProps(workInProgress2, instance, newProps, nextContext) {
        workInProgress2 = instance.state;
        "function" === typeof instance.componentWillReceiveProps && instance.componentWillReceiveProps(newProps, nextContext);
        "function" === typeof instance.UNSAFE_componentWillReceiveProps && instance.UNSAFE_componentWillReceiveProps(newProps, nextContext);
        instance.state !== workInProgress2 && classComponentUpdater.enqueueReplaceState(instance, instance.state, null);
      }
      function resolveClassComponentProps(Component, baseProps) {
        var newProps = baseProps;
        if ("ref" in baseProps) {
          newProps = {};
          for (var propName in baseProps)
            "ref" !== propName && (newProps[propName] = baseProps[propName]);
        }
        if (Component = Component.defaultProps) {
          newProps === baseProps && (newProps = assign({}, newProps));
          for (var propName$73 in Component)
            void 0 === newProps[propName$73] && (newProps[propName$73] = Component[propName$73]);
        }
        return newProps;
      }
      function defaultOnUncaughtError(error) {
        reportGlobalError(error);
      }
      function defaultOnCaughtError(error) {
        console.error(error);
      }
      function defaultOnRecoverableError(error) {
        reportGlobalError(error);
      }
      function logUncaughtError(root2, errorInfo) {
        try {
          var onUncaughtError = root2.onUncaughtError;
          onUncaughtError(errorInfo.value, { componentStack: errorInfo.stack });
        } catch (e$74) {
          setTimeout(function() {
            throw e$74;
          });
        }
      }
      function logCaughtError(root2, boundary, errorInfo) {
        try {
          var onCaughtError = root2.onCaughtError;
          onCaughtError(errorInfo.value, {
            componentStack: errorInfo.stack,
            errorBoundary: 1 === boundary.tag ? boundary.stateNode : null
          });
        } catch (e$75) {
          setTimeout(function() {
            throw e$75;
          });
        }
      }
      function createRootErrorUpdate(root2, errorInfo, lane) {
        lane = createUpdate(lane);
        lane.tag = 3;
        lane.payload = { element: null };
        lane.callback = function() {
          logUncaughtError(root2, errorInfo);
        };
        return lane;
      }
      function createClassErrorUpdate(lane) {
        lane = createUpdate(lane);
        lane.tag = 3;
        return lane;
      }
      function initializeClassErrorUpdate(update, root2, fiber, errorInfo) {
        var getDerivedStateFromError = fiber.type.getDerivedStateFromError;
        if ("function" === typeof getDerivedStateFromError) {
          var error = errorInfo.value;
          update.payload = function() {
            return getDerivedStateFromError(error);
          };
          update.callback = function() {
            logCaughtError(root2, fiber, errorInfo);
          };
        }
        var inst = fiber.stateNode;
        null !== inst && "function" === typeof inst.componentDidCatch && (update.callback = function() {
          logCaughtError(root2, fiber, errorInfo);
          "function" !== typeof getDerivedStateFromError && (null === legacyErrorBoundariesThatAlreadyFailed ? legacyErrorBoundariesThatAlreadyFailed = /* @__PURE__ */ new Set([this]) : legacyErrorBoundariesThatAlreadyFailed.add(this));
          var stack = errorInfo.stack;
          this.componentDidCatch(errorInfo.value, {
            componentStack: null !== stack ? stack : ""
          });
        });
      }
      function throwException(root2, returnFiber, sourceFiber, value, rootRenderLanes) {
        sourceFiber.flags |= 32768;
        if (null !== value && "object" === typeof value && "function" === typeof value.then) {
          returnFiber = sourceFiber.alternate;
          null !== returnFiber && propagateParentContextChanges(
            returnFiber,
            sourceFiber,
            rootRenderLanes,
            true
          );
          sourceFiber = suspenseHandlerStackCursor.current;
          if (null !== sourceFiber) {
            switch (sourceFiber.tag) {
              case 31:
              case 13:
                return null === shellBoundary ? renderDidSuspendDelayIfPossible() : null === sourceFiber.alternate && 0 === workInProgressRootExitStatus && (workInProgressRootExitStatus = 3), sourceFiber.flags &= -257, sourceFiber.flags |= 65536, sourceFiber.lanes = rootRenderLanes, value === noopSuspenseyCommitThenable ? sourceFiber.flags |= 16384 : (returnFiber = sourceFiber.updateQueue, null === returnFiber ? sourceFiber.updateQueue = /* @__PURE__ */ new Set([value]) : returnFiber.add(value), attachPingListener(root2, value, rootRenderLanes)), false;
              case 22:
                return sourceFiber.flags |= 65536, value === noopSuspenseyCommitThenable ? sourceFiber.flags |= 16384 : (returnFiber = sourceFiber.updateQueue, null === returnFiber ? (returnFiber = {
                  transitions: null,
                  markerInstances: null,
                  retryQueue: /* @__PURE__ */ new Set([value])
                }, sourceFiber.updateQueue = returnFiber) : (sourceFiber = returnFiber.retryQueue, null === sourceFiber ? returnFiber.retryQueue = /* @__PURE__ */ new Set([value]) : sourceFiber.add(value)), attachPingListener(root2, value, rootRenderLanes)), false;
            }
            throw Error(formatProdErrorMessage(435, sourceFiber.tag));
          }
          attachPingListener(root2, value, rootRenderLanes);
          renderDidSuspendDelayIfPossible();
          return false;
        }
        if (isHydrating)
          return returnFiber = suspenseHandlerStackCursor.current, null !== returnFiber ? (0 === (returnFiber.flags & 65536) && (returnFiber.flags |= 256), returnFiber.flags |= 65536, returnFiber.lanes = rootRenderLanes, value !== HydrationMismatchException && (root2 = Error(formatProdErrorMessage(422), { cause: value }), queueHydrationError(createCapturedValueAtFiber(root2, sourceFiber)))) : (value !== HydrationMismatchException && (returnFiber = Error(formatProdErrorMessage(423), {
            cause: value
          }), queueHydrationError(
            createCapturedValueAtFiber(returnFiber, sourceFiber)
          )), root2 = root2.current.alternate, root2.flags |= 65536, rootRenderLanes &= -rootRenderLanes, root2.lanes |= rootRenderLanes, value = createCapturedValueAtFiber(value, sourceFiber), rootRenderLanes = createRootErrorUpdate(
            root2.stateNode,
            value,
            rootRenderLanes
          ), enqueueCapturedUpdate(root2, rootRenderLanes), 4 !== workInProgressRootExitStatus && (workInProgressRootExitStatus = 2)), false;
        var wrapperError = Error(formatProdErrorMessage(520), { cause: value });
        wrapperError = createCapturedValueAtFiber(wrapperError, sourceFiber);
        null === workInProgressRootConcurrentErrors ? workInProgressRootConcurrentErrors = [wrapperError] : workInProgressRootConcurrentErrors.push(wrapperError);
        4 !== workInProgressRootExitStatus && (workInProgressRootExitStatus = 2);
        if (null === returnFiber) return true;
        value = createCapturedValueAtFiber(value, sourceFiber);
        sourceFiber = returnFiber;
        do {
          switch (sourceFiber.tag) {
            case 3:
              return sourceFiber.flags |= 65536, root2 = rootRenderLanes & -rootRenderLanes, sourceFiber.lanes |= root2, root2 = createRootErrorUpdate(sourceFiber.stateNode, value, root2), enqueueCapturedUpdate(sourceFiber, root2), false;
            case 1:
              if (returnFiber = sourceFiber.type, wrapperError = sourceFiber.stateNode, 0 === (sourceFiber.flags & 128) && ("function" === typeof returnFiber.getDerivedStateFromError || null !== wrapperError && "function" === typeof wrapperError.componentDidCatch && (null === legacyErrorBoundariesThatAlreadyFailed || !legacyErrorBoundariesThatAlreadyFailed.has(wrapperError))))
                return sourceFiber.flags |= 65536, rootRenderLanes &= -rootRenderLanes, sourceFiber.lanes |= rootRenderLanes, rootRenderLanes = createClassErrorUpdate(rootRenderLanes), initializeClassErrorUpdate(
                  rootRenderLanes,
                  root2,
                  sourceFiber,
                  value
                ), enqueueCapturedUpdate(sourceFiber, rootRenderLanes), false;
          }
          sourceFiber = sourceFiber.return;
        } while (null !== sourceFiber);
        return false;
      }
      var SelectiveHydrationException = Error(formatProdErrorMessage(461));
      var didReceiveUpdate = false;
      function reconcileChildren(current, workInProgress2, nextChildren, renderLanes2) {
        workInProgress2.child = null === current ? mountChildFibers(workInProgress2, null, nextChildren, renderLanes2) : reconcileChildFibers(
          workInProgress2,
          current.child,
          nextChildren,
          renderLanes2
        );
      }
      function updateForwardRef(current, workInProgress2, Component, nextProps, renderLanes2) {
        Component = Component.render;
        var ref = workInProgress2.ref;
        if ("ref" in nextProps) {
          var propsWithoutRef = {};
          for (var key in nextProps)
            "ref" !== key && (propsWithoutRef[key] = nextProps[key]);
        } else propsWithoutRef = nextProps;
        prepareToReadContext(workInProgress2);
        nextProps = renderWithHooks(
          current,
          workInProgress2,
          Component,
          propsWithoutRef,
          ref,
          renderLanes2
        );
        key = checkDidRenderIdHook();
        if (null !== current && !didReceiveUpdate)
          return bailoutHooks(current, workInProgress2, renderLanes2), bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
        isHydrating && key && pushMaterializedTreeId(workInProgress2);
        workInProgress2.flags |= 1;
        reconcileChildren(current, workInProgress2, nextProps, renderLanes2);
        return workInProgress2.child;
      }
      function updateMemoComponent(current, workInProgress2, Component, nextProps, renderLanes2) {
        if (null === current) {
          var type = Component.type;
          if ("function" === typeof type && !shouldConstruct(type) && void 0 === type.defaultProps && null === Component.compare)
            return workInProgress2.tag = 15, workInProgress2.type = type, updateSimpleMemoComponent(
              current,
              workInProgress2,
              type,
              nextProps,
              renderLanes2
            );
          current = createFiberFromTypeAndProps(
            Component.type,
            null,
            nextProps,
            workInProgress2,
            workInProgress2.mode,
            renderLanes2
          );
          current.ref = workInProgress2.ref;
          current.return = workInProgress2;
          return workInProgress2.child = current;
        }
        type = current.child;
        if (!checkScheduledUpdateOrContext(current, renderLanes2)) {
          var prevProps = type.memoizedProps;
          Component = Component.compare;
          Component = null !== Component ? Component : shallowEqual;
          if (Component(prevProps, nextProps) && current.ref === workInProgress2.ref)
            return bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
        }
        workInProgress2.flags |= 1;
        current = createWorkInProgress(type, nextProps);
        current.ref = workInProgress2.ref;
        current.return = workInProgress2;
        return workInProgress2.child = current;
      }
      function updateSimpleMemoComponent(current, workInProgress2, Component, nextProps, renderLanes2) {
        if (null !== current) {
          var prevProps = current.memoizedProps;
          if (shallowEqual(prevProps, nextProps) && current.ref === workInProgress2.ref)
            if (didReceiveUpdate = false, workInProgress2.pendingProps = nextProps = prevProps, checkScheduledUpdateOrContext(current, renderLanes2))
              0 !== (current.flags & 131072) && (didReceiveUpdate = true);
            else
              return workInProgress2.lanes = current.lanes, bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
        }
        return updateFunctionComponent(
          current,
          workInProgress2,
          Component,
          nextProps,
          renderLanes2
        );
      }
      function updateOffscreenComponent(current, workInProgress2, renderLanes2, nextProps) {
        var nextChildren = nextProps.children, prevState = null !== current ? current.memoizedState : null;
        null === current && null === workInProgress2.stateNode && (workInProgress2.stateNode = {
          _visibility: 1,
          _pendingMarkers: null,
          _retryCache: null,
          _transitions: null
        });
        if ("hidden" === nextProps.mode) {
          if (0 !== (workInProgress2.flags & 128)) {
            prevState = null !== prevState ? prevState.baseLanes | renderLanes2 : renderLanes2;
            if (null !== current) {
              nextProps = workInProgress2.child = current.child;
              for (nextChildren = 0; null !== nextProps; )
                nextChildren = nextChildren | nextProps.lanes | nextProps.childLanes, nextProps = nextProps.sibling;
              nextProps = nextChildren & ~prevState;
            } else nextProps = 0, workInProgress2.child = null;
            return deferHiddenOffscreenComponent(
              current,
              workInProgress2,
              prevState,
              renderLanes2,
              nextProps
            );
          }
          if (0 !== (renderLanes2 & 536870912))
            workInProgress2.memoizedState = { baseLanes: 0, cachePool: null }, null !== current && pushTransition(
              workInProgress2,
              null !== prevState ? prevState.cachePool : null
            ), null !== prevState ? pushHiddenContext(workInProgress2, prevState) : reuseHiddenContextOnStack(), pushOffscreenSuspenseHandler(workInProgress2);
          else
            return nextProps = workInProgress2.lanes = 536870912, deferHiddenOffscreenComponent(
              current,
              workInProgress2,
              null !== prevState ? prevState.baseLanes | renderLanes2 : renderLanes2,
              renderLanes2,
              nextProps
            );
        } else
          null !== prevState ? (pushTransition(workInProgress2, prevState.cachePool), pushHiddenContext(workInProgress2, prevState), reuseSuspenseHandlerOnStack(workInProgress2), workInProgress2.memoizedState = null) : (null !== current && pushTransition(workInProgress2, null), reuseHiddenContextOnStack(), reuseSuspenseHandlerOnStack(workInProgress2));
        reconcileChildren(current, workInProgress2, nextChildren, renderLanes2);
        return workInProgress2.child;
      }
      function bailoutOffscreenComponent(current, workInProgress2) {
        null !== current && 22 === current.tag || null !== workInProgress2.stateNode || (workInProgress2.stateNode = {
          _visibility: 1,
          _pendingMarkers: null,
          _retryCache: null,
          _transitions: null
        });
        return workInProgress2.sibling;
      }
      function deferHiddenOffscreenComponent(current, workInProgress2, nextBaseLanes, renderLanes2, remainingChildLanes) {
        var JSCompiler_inline_result = peekCacheFromPool();
        JSCompiler_inline_result = null === JSCompiler_inline_result ? null : { parent: CacheContext._currentValue, pool: JSCompiler_inline_result };
        workInProgress2.memoizedState = {
          baseLanes: nextBaseLanes,
          cachePool: JSCompiler_inline_result
        };
        null !== current && pushTransition(workInProgress2, null);
        reuseHiddenContextOnStack();
        pushOffscreenSuspenseHandler(workInProgress2);
        null !== current && propagateParentContextChanges(current, workInProgress2, renderLanes2, true);
        workInProgress2.childLanes = remainingChildLanes;
        return null;
      }
      function mountActivityChildren(workInProgress2, nextProps) {
        nextProps = mountWorkInProgressOffscreenFiber(
          { mode: nextProps.mode, children: nextProps.children },
          workInProgress2.mode
        );
        nextProps.ref = workInProgress2.ref;
        workInProgress2.child = nextProps;
        nextProps.return = workInProgress2;
        return nextProps;
      }
      function retryActivityComponentWithoutHydrating(current, workInProgress2, renderLanes2) {
        reconcileChildFibers(workInProgress2, current.child, null, renderLanes2);
        current = mountActivityChildren(workInProgress2, workInProgress2.pendingProps);
        current.flags |= 2;
        popSuspenseHandler(workInProgress2);
        workInProgress2.memoizedState = null;
        return current;
      }
      function updateActivityComponent(current, workInProgress2, renderLanes2) {
        var nextProps = workInProgress2.pendingProps, didSuspend = 0 !== (workInProgress2.flags & 128);
        workInProgress2.flags &= -129;
        if (null === current) {
          if (isHydrating) {
            if ("hidden" === nextProps.mode)
              return current = mountActivityChildren(workInProgress2, nextProps), workInProgress2.lanes = 536870912, bailoutOffscreenComponent(null, current);
            pushDehydratedActivitySuspenseHandler(workInProgress2);
            (current = nextHydratableInstance) ? (current = canHydrateHydrationBoundary(
              current,
              rootOrSingletonContext
            ), current = null !== current && "&" === current.data ? current : null, null !== current && (workInProgress2.memoizedState = {
              dehydrated: current,
              treeContext: null !== treeContextProvider ? { id: treeContextId, overflow: treeContextOverflow } : null,
              retryLane: 536870912,
              hydrationErrors: null
            }, renderLanes2 = createFiberFromDehydratedFragment(current), renderLanes2.return = workInProgress2, workInProgress2.child = renderLanes2, hydrationParentFiber = workInProgress2, nextHydratableInstance = null)) : current = null;
            if (null === current) throw throwOnHydrationMismatch(workInProgress2);
            workInProgress2.lanes = 536870912;
            return null;
          }
          return mountActivityChildren(workInProgress2, nextProps);
        }
        var prevState = current.memoizedState;
        if (null !== prevState) {
          var dehydrated = prevState.dehydrated;
          pushDehydratedActivitySuspenseHandler(workInProgress2);
          if (didSuspend)
            if (workInProgress2.flags & 256)
              workInProgress2.flags &= -257, workInProgress2 = retryActivityComponentWithoutHydrating(
                current,
                workInProgress2,
                renderLanes2
              );
            else if (null !== workInProgress2.memoizedState)
              workInProgress2.child = current.child, workInProgress2.flags |= 128, workInProgress2 = null;
            else throw Error(formatProdErrorMessage(558));
          else if (didReceiveUpdate || propagateParentContextChanges(current, workInProgress2, renderLanes2, false), didSuspend = 0 !== (renderLanes2 & current.childLanes), didReceiveUpdate || didSuspend) {
            nextProps = workInProgressRoot;
            if (null !== nextProps && (dehydrated = getBumpedLaneForHydration(nextProps, renderLanes2), 0 !== dehydrated && dehydrated !== prevState.retryLane))
              throw prevState.retryLane = dehydrated, enqueueConcurrentRenderForLane(current, dehydrated), scheduleUpdateOnFiber(nextProps, current, dehydrated), SelectiveHydrationException;
            renderDidSuspendDelayIfPossible();
            workInProgress2 = retryActivityComponentWithoutHydrating(
              current,
              workInProgress2,
              renderLanes2
            );
          } else
            current = prevState.treeContext, nextHydratableInstance = getNextHydratable(dehydrated.nextSibling), hydrationParentFiber = workInProgress2, isHydrating = true, hydrationErrors = null, rootOrSingletonContext = false, null !== current && restoreSuspendedTreeContext(workInProgress2, current), workInProgress2 = mountActivityChildren(workInProgress2, nextProps), workInProgress2.flags |= 4096;
          return workInProgress2;
        }
        current = createWorkInProgress(current.child, {
          mode: nextProps.mode,
          children: nextProps.children
        });
        current.ref = workInProgress2.ref;
        workInProgress2.child = current;
        current.return = workInProgress2;
        return current;
      }
      function markRef(current, workInProgress2) {
        var ref = workInProgress2.ref;
        if (null === ref)
          null !== current && null !== current.ref && (workInProgress2.flags |= 4194816);
        else {
          if ("function" !== typeof ref && "object" !== typeof ref)
            throw Error(formatProdErrorMessage(284));
          if (null === current || current.ref !== ref)
            workInProgress2.flags |= 4194816;
        }
      }
      function updateFunctionComponent(current, workInProgress2, Component, nextProps, renderLanes2) {
        prepareToReadContext(workInProgress2);
        Component = renderWithHooks(
          current,
          workInProgress2,
          Component,
          nextProps,
          void 0,
          renderLanes2
        );
        nextProps = checkDidRenderIdHook();
        if (null !== current && !didReceiveUpdate)
          return bailoutHooks(current, workInProgress2, renderLanes2), bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
        isHydrating && nextProps && pushMaterializedTreeId(workInProgress2);
        workInProgress2.flags |= 1;
        reconcileChildren(current, workInProgress2, Component, renderLanes2);
        return workInProgress2.child;
      }
      function replayFunctionComponent(current, workInProgress2, nextProps, Component, secondArg, renderLanes2) {
        prepareToReadContext(workInProgress2);
        workInProgress2.updateQueue = null;
        nextProps = renderWithHooksAgain(
          workInProgress2,
          Component,
          nextProps,
          secondArg
        );
        finishRenderingHooks(current);
        Component = checkDidRenderIdHook();
        if (null !== current && !didReceiveUpdate)
          return bailoutHooks(current, workInProgress2, renderLanes2), bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
        isHydrating && Component && pushMaterializedTreeId(workInProgress2);
        workInProgress2.flags |= 1;
        reconcileChildren(current, workInProgress2, nextProps, renderLanes2);
        return workInProgress2.child;
      }
      function updateClassComponent(current, workInProgress2, Component, nextProps, renderLanes2) {
        prepareToReadContext(workInProgress2);
        if (null === workInProgress2.stateNode) {
          var context = emptyContextObject, contextType = Component.contextType;
          "object" === typeof contextType && null !== contextType && (context = readContext(contextType));
          context = new Component(nextProps, context);
          workInProgress2.memoizedState = null !== context.state && void 0 !== context.state ? context.state : null;
          context.updater = classComponentUpdater;
          workInProgress2.stateNode = context;
          context._reactInternals = workInProgress2;
          context = workInProgress2.stateNode;
          context.props = nextProps;
          context.state = workInProgress2.memoizedState;
          context.refs = {};
          initializeUpdateQueue(workInProgress2);
          contextType = Component.contextType;
          context.context = "object" === typeof contextType && null !== contextType ? readContext(contextType) : emptyContextObject;
          context.state = workInProgress2.memoizedState;
          contextType = Component.getDerivedStateFromProps;
          "function" === typeof contextType && (applyDerivedStateFromProps(
            workInProgress2,
            Component,
            contextType,
            nextProps
          ), context.state = workInProgress2.memoizedState);
          "function" === typeof Component.getDerivedStateFromProps || "function" === typeof context.getSnapshotBeforeUpdate || "function" !== typeof context.UNSAFE_componentWillMount && "function" !== typeof context.componentWillMount || (contextType = context.state, "function" === typeof context.componentWillMount && context.componentWillMount(), "function" === typeof context.UNSAFE_componentWillMount && context.UNSAFE_componentWillMount(), contextType !== context.state && classComponentUpdater.enqueueReplaceState(context, context.state, null), processUpdateQueue(workInProgress2, nextProps, context, renderLanes2), suspendIfUpdateReadFromEntangledAsyncAction(), context.state = workInProgress2.memoizedState);
          "function" === typeof context.componentDidMount && (workInProgress2.flags |= 4194308);
          nextProps = true;
        } else if (null === current) {
          context = workInProgress2.stateNode;
          var unresolvedOldProps = workInProgress2.memoizedProps, oldProps = resolveClassComponentProps(Component, unresolvedOldProps);
          context.props = oldProps;
          var oldContext = context.context, contextType$jscomp$0 = Component.contextType;
          contextType = emptyContextObject;
          "object" === typeof contextType$jscomp$0 && null !== contextType$jscomp$0 && (contextType = readContext(contextType$jscomp$0));
          var getDerivedStateFromProps = Component.getDerivedStateFromProps;
          contextType$jscomp$0 = "function" === typeof getDerivedStateFromProps || "function" === typeof context.getSnapshotBeforeUpdate;
          unresolvedOldProps = workInProgress2.pendingProps !== unresolvedOldProps;
          contextType$jscomp$0 || "function" !== typeof context.UNSAFE_componentWillReceiveProps && "function" !== typeof context.componentWillReceiveProps || (unresolvedOldProps || oldContext !== contextType) && callComponentWillReceiveProps(
            workInProgress2,
            context,
            nextProps,
            contextType
          );
          hasForceUpdate = false;
          var oldState = workInProgress2.memoizedState;
          context.state = oldState;
          processUpdateQueue(workInProgress2, nextProps, context, renderLanes2);
          suspendIfUpdateReadFromEntangledAsyncAction();
          oldContext = workInProgress2.memoizedState;
          unresolvedOldProps || oldState !== oldContext || hasForceUpdate ? ("function" === typeof getDerivedStateFromProps && (applyDerivedStateFromProps(
            workInProgress2,
            Component,
            getDerivedStateFromProps,
            nextProps
          ), oldContext = workInProgress2.memoizedState), (oldProps = hasForceUpdate || checkShouldComponentUpdate(
            workInProgress2,
            Component,
            oldProps,
            nextProps,
            oldState,
            oldContext,
            contextType
          )) ? (contextType$jscomp$0 || "function" !== typeof context.UNSAFE_componentWillMount && "function" !== typeof context.componentWillMount || ("function" === typeof context.componentWillMount && context.componentWillMount(), "function" === typeof context.UNSAFE_componentWillMount && context.UNSAFE_componentWillMount()), "function" === typeof context.componentDidMount && (workInProgress2.flags |= 4194308)) : ("function" === typeof context.componentDidMount && (workInProgress2.flags |= 4194308), workInProgress2.memoizedProps = nextProps, workInProgress2.memoizedState = oldContext), context.props = nextProps, context.state = oldContext, context.context = contextType, nextProps = oldProps) : ("function" === typeof context.componentDidMount && (workInProgress2.flags |= 4194308), nextProps = false);
        } else {
          context = workInProgress2.stateNode;
          cloneUpdateQueue(current, workInProgress2);
          contextType = workInProgress2.memoizedProps;
          contextType$jscomp$0 = resolveClassComponentProps(Component, contextType);
          context.props = contextType$jscomp$0;
          getDerivedStateFromProps = workInProgress2.pendingProps;
          oldState = context.context;
          oldContext = Component.contextType;
          oldProps = emptyContextObject;
          "object" === typeof oldContext && null !== oldContext && (oldProps = readContext(oldContext));
          unresolvedOldProps = Component.getDerivedStateFromProps;
          (oldContext = "function" === typeof unresolvedOldProps || "function" === typeof context.getSnapshotBeforeUpdate) || "function" !== typeof context.UNSAFE_componentWillReceiveProps && "function" !== typeof context.componentWillReceiveProps || (contextType !== getDerivedStateFromProps || oldState !== oldProps) && callComponentWillReceiveProps(
            workInProgress2,
            context,
            nextProps,
            oldProps
          );
          hasForceUpdate = false;
          oldState = workInProgress2.memoizedState;
          context.state = oldState;
          processUpdateQueue(workInProgress2, nextProps, context, renderLanes2);
          suspendIfUpdateReadFromEntangledAsyncAction();
          var newState = workInProgress2.memoizedState;
          contextType !== getDerivedStateFromProps || oldState !== newState || hasForceUpdate || null !== current && null !== current.dependencies && checkIfContextChanged(current.dependencies) ? ("function" === typeof unresolvedOldProps && (applyDerivedStateFromProps(
            workInProgress2,
            Component,
            unresolvedOldProps,
            nextProps
          ), newState = workInProgress2.memoizedState), (contextType$jscomp$0 = hasForceUpdate || checkShouldComponentUpdate(
            workInProgress2,
            Component,
            contextType$jscomp$0,
            nextProps,
            oldState,
            newState,
            oldProps
          ) || null !== current && null !== current.dependencies && checkIfContextChanged(current.dependencies)) ? (oldContext || "function" !== typeof context.UNSAFE_componentWillUpdate && "function" !== typeof context.componentWillUpdate || ("function" === typeof context.componentWillUpdate && context.componentWillUpdate(nextProps, newState, oldProps), "function" === typeof context.UNSAFE_componentWillUpdate && context.UNSAFE_componentWillUpdate(
            nextProps,
            newState,
            oldProps
          )), "function" === typeof context.componentDidUpdate && (workInProgress2.flags |= 4), "function" === typeof context.getSnapshotBeforeUpdate && (workInProgress2.flags |= 1024)) : ("function" !== typeof context.componentDidUpdate || contextType === current.memoizedProps && oldState === current.memoizedState || (workInProgress2.flags |= 4), "function" !== typeof context.getSnapshotBeforeUpdate || contextType === current.memoizedProps && oldState === current.memoizedState || (workInProgress2.flags |= 1024), workInProgress2.memoizedProps = nextProps, workInProgress2.memoizedState = newState), context.props = nextProps, context.state = newState, context.context = oldProps, nextProps = contextType$jscomp$0) : ("function" !== typeof context.componentDidUpdate || contextType === current.memoizedProps && oldState === current.memoizedState || (workInProgress2.flags |= 4), "function" !== typeof context.getSnapshotBeforeUpdate || contextType === current.memoizedProps && oldState === current.memoizedState || (workInProgress2.flags |= 1024), nextProps = false);
        }
        context = nextProps;
        markRef(current, workInProgress2);
        nextProps = 0 !== (workInProgress2.flags & 128);
        context || nextProps ? (context = workInProgress2.stateNode, Component = nextProps && "function" !== typeof Component.getDerivedStateFromError ? null : context.render(), workInProgress2.flags |= 1, null !== current && nextProps ? (workInProgress2.child = reconcileChildFibers(
          workInProgress2,
          current.child,
          null,
          renderLanes2
        ), workInProgress2.child = reconcileChildFibers(
          workInProgress2,
          null,
          Component,
          renderLanes2
        )) : reconcileChildren(current, workInProgress2, Component, renderLanes2), workInProgress2.memoizedState = context.state, current = workInProgress2.child) : current = bailoutOnAlreadyFinishedWork(
          current,
          workInProgress2,
          renderLanes2
        );
        return current;
      }
      function mountHostRootWithoutHydrating(current, workInProgress2, nextChildren, renderLanes2) {
        resetHydrationState();
        workInProgress2.flags |= 256;
        reconcileChildren(current, workInProgress2, nextChildren, renderLanes2);
        return workInProgress2.child;
      }
      var SUSPENDED_MARKER = {
        dehydrated: null,
        treeContext: null,
        retryLane: 0,
        hydrationErrors: null
      };
      function mountSuspenseOffscreenState(renderLanes2) {
        return { baseLanes: renderLanes2, cachePool: getSuspendedCache() };
      }
      function getRemainingWorkInPrimaryTree(current, primaryTreeDidDefer, renderLanes2) {
        current = null !== current ? current.childLanes & ~renderLanes2 : 0;
        primaryTreeDidDefer && (current |= workInProgressDeferredLane);
        return current;
      }
      function updateSuspenseComponent(current, workInProgress2, renderLanes2) {
        var nextProps = workInProgress2.pendingProps, showFallback = false, didSuspend = 0 !== (workInProgress2.flags & 128), JSCompiler_temp;
        (JSCompiler_temp = didSuspend) || (JSCompiler_temp = null !== current && null === current.memoizedState ? false : 0 !== (suspenseStackCursor.current & 2));
        JSCompiler_temp && (showFallback = true, workInProgress2.flags &= -129);
        JSCompiler_temp = 0 !== (workInProgress2.flags & 32);
        workInProgress2.flags &= -33;
        if (null === current) {
          if (isHydrating) {
            showFallback ? pushPrimaryTreeSuspenseHandler(workInProgress2) : reuseSuspenseHandlerOnStack(workInProgress2);
            (current = nextHydratableInstance) ? (current = canHydrateHydrationBoundary(
              current,
              rootOrSingletonContext
            ), current = null !== current && "&" !== current.data ? current : null, null !== current && (workInProgress2.memoizedState = {
              dehydrated: current,
              treeContext: null !== treeContextProvider ? { id: treeContextId, overflow: treeContextOverflow } : null,
              retryLane: 536870912,
              hydrationErrors: null
            }, renderLanes2 = createFiberFromDehydratedFragment(current), renderLanes2.return = workInProgress2, workInProgress2.child = renderLanes2, hydrationParentFiber = workInProgress2, nextHydratableInstance = null)) : current = null;
            if (null === current) throw throwOnHydrationMismatch(workInProgress2);
            isSuspenseInstanceFallback(current) ? workInProgress2.lanes = 32 : workInProgress2.lanes = 536870912;
            return null;
          }
          var nextPrimaryChildren = nextProps.children;
          nextProps = nextProps.fallback;
          if (showFallback)
            return reuseSuspenseHandlerOnStack(workInProgress2), showFallback = workInProgress2.mode, nextPrimaryChildren = mountWorkInProgressOffscreenFiber(
              { mode: "hidden", children: nextPrimaryChildren },
              showFallback
            ), nextProps = createFiberFromFragment(
              nextProps,
              showFallback,
              renderLanes2,
              null
            ), nextPrimaryChildren.return = workInProgress2, nextProps.return = workInProgress2, nextPrimaryChildren.sibling = nextProps, workInProgress2.child = nextPrimaryChildren, nextProps = workInProgress2.child, nextProps.memoizedState = mountSuspenseOffscreenState(renderLanes2), nextProps.childLanes = getRemainingWorkInPrimaryTree(
              current,
              JSCompiler_temp,
              renderLanes2
            ), workInProgress2.memoizedState = SUSPENDED_MARKER, bailoutOffscreenComponent(null, nextProps);
          pushPrimaryTreeSuspenseHandler(workInProgress2);
          return mountSuspensePrimaryChildren(workInProgress2, nextPrimaryChildren);
        }
        var prevState = current.memoizedState;
        if (null !== prevState && (nextPrimaryChildren = prevState.dehydrated, null !== nextPrimaryChildren)) {
          if (didSuspend)
            workInProgress2.flags & 256 ? (pushPrimaryTreeSuspenseHandler(workInProgress2), workInProgress2.flags &= -257, workInProgress2 = retrySuspenseComponentWithoutHydrating(
              current,
              workInProgress2,
              renderLanes2
            )) : null !== workInProgress2.memoizedState ? (reuseSuspenseHandlerOnStack(workInProgress2), workInProgress2.child = current.child, workInProgress2.flags |= 128, workInProgress2 = null) : (reuseSuspenseHandlerOnStack(workInProgress2), nextPrimaryChildren = nextProps.fallback, showFallback = workInProgress2.mode, nextProps = mountWorkInProgressOffscreenFiber(
              { mode: "visible", children: nextProps.children },
              showFallback
            ), nextPrimaryChildren = createFiberFromFragment(
              nextPrimaryChildren,
              showFallback,
              renderLanes2,
              null
            ), nextPrimaryChildren.flags |= 2, nextProps.return = workInProgress2, nextPrimaryChildren.return = workInProgress2, nextProps.sibling = nextPrimaryChildren, workInProgress2.child = nextProps, reconcileChildFibers(
              workInProgress2,
              current.child,
              null,
              renderLanes2
            ), nextProps = workInProgress2.child, nextProps.memoizedState = mountSuspenseOffscreenState(renderLanes2), nextProps.childLanes = getRemainingWorkInPrimaryTree(
              current,
              JSCompiler_temp,
              renderLanes2
            ), workInProgress2.memoizedState = SUSPENDED_MARKER, workInProgress2 = bailoutOffscreenComponent(null, nextProps));
          else if (pushPrimaryTreeSuspenseHandler(workInProgress2), isSuspenseInstanceFallback(nextPrimaryChildren)) {
            JSCompiler_temp = nextPrimaryChildren.nextSibling && nextPrimaryChildren.nextSibling.dataset;
            if (JSCompiler_temp) var digest = JSCompiler_temp.dgst;
            JSCompiler_temp = digest;
            nextProps = Error(formatProdErrorMessage(419));
            nextProps.stack = "";
            nextProps.digest = JSCompiler_temp;
            queueHydrationError({ value: nextProps, source: null, stack: null });
            workInProgress2 = retrySuspenseComponentWithoutHydrating(
              current,
              workInProgress2,
              renderLanes2
            );
          } else if (didReceiveUpdate || propagateParentContextChanges(current, workInProgress2, renderLanes2, false), JSCompiler_temp = 0 !== (renderLanes2 & current.childLanes), didReceiveUpdate || JSCompiler_temp) {
            JSCompiler_temp = workInProgressRoot;
            if (null !== JSCompiler_temp && (nextProps = getBumpedLaneForHydration(JSCompiler_temp, renderLanes2), 0 !== nextProps && nextProps !== prevState.retryLane))
              throw prevState.retryLane = nextProps, enqueueConcurrentRenderForLane(current, nextProps), scheduleUpdateOnFiber(JSCompiler_temp, current, nextProps), SelectiveHydrationException;
            isSuspenseInstancePending(nextPrimaryChildren) || renderDidSuspendDelayIfPossible();
            workInProgress2 = retrySuspenseComponentWithoutHydrating(
              current,
              workInProgress2,
              renderLanes2
            );
          } else
            isSuspenseInstancePending(nextPrimaryChildren) ? (workInProgress2.flags |= 192, workInProgress2.child = current.child, workInProgress2 = null) : (current = prevState.treeContext, nextHydratableInstance = getNextHydratable(
              nextPrimaryChildren.nextSibling
            ), hydrationParentFiber = workInProgress2, isHydrating = true, hydrationErrors = null, rootOrSingletonContext = false, null !== current && restoreSuspendedTreeContext(workInProgress2, current), workInProgress2 = mountSuspensePrimaryChildren(
              workInProgress2,
              nextProps.children
            ), workInProgress2.flags |= 4096);
          return workInProgress2;
        }
        if (showFallback)
          return reuseSuspenseHandlerOnStack(workInProgress2), nextPrimaryChildren = nextProps.fallback, showFallback = workInProgress2.mode, prevState = current.child, digest = prevState.sibling, nextProps = createWorkInProgress(prevState, {
            mode: "hidden",
            children: nextProps.children
          }), nextProps.subtreeFlags = prevState.subtreeFlags & 65011712, null !== digest ? nextPrimaryChildren = createWorkInProgress(
            digest,
            nextPrimaryChildren
          ) : (nextPrimaryChildren = createFiberFromFragment(
            nextPrimaryChildren,
            showFallback,
            renderLanes2,
            null
          ), nextPrimaryChildren.flags |= 2), nextPrimaryChildren.return = workInProgress2, nextProps.return = workInProgress2, nextProps.sibling = nextPrimaryChildren, workInProgress2.child = nextProps, bailoutOffscreenComponent(null, nextProps), nextProps = workInProgress2.child, nextPrimaryChildren = current.child.memoizedState, null === nextPrimaryChildren ? nextPrimaryChildren = mountSuspenseOffscreenState(renderLanes2) : (showFallback = nextPrimaryChildren.cachePool, null !== showFallback ? (prevState = CacheContext._currentValue, showFallback = showFallback.parent !== prevState ? { parent: prevState, pool: prevState } : showFallback) : showFallback = getSuspendedCache(), nextPrimaryChildren = {
            baseLanes: nextPrimaryChildren.baseLanes | renderLanes2,
            cachePool: showFallback
          }), nextProps.memoizedState = nextPrimaryChildren, nextProps.childLanes = getRemainingWorkInPrimaryTree(
            current,
            JSCompiler_temp,
            renderLanes2
          ), workInProgress2.memoizedState = SUSPENDED_MARKER, bailoutOffscreenComponent(current.child, nextProps);
        pushPrimaryTreeSuspenseHandler(workInProgress2);
        renderLanes2 = current.child;
        current = renderLanes2.sibling;
        renderLanes2 = createWorkInProgress(renderLanes2, {
          mode: "visible",
          children: nextProps.children
        });
        renderLanes2.return = workInProgress2;
        renderLanes2.sibling = null;
        null !== current && (JSCompiler_temp = workInProgress2.deletions, null === JSCompiler_temp ? (workInProgress2.deletions = [current], workInProgress2.flags |= 16) : JSCompiler_temp.push(current));
        workInProgress2.child = renderLanes2;
        workInProgress2.memoizedState = null;
        return renderLanes2;
      }
      function mountSuspensePrimaryChildren(workInProgress2, primaryChildren) {
        primaryChildren = mountWorkInProgressOffscreenFiber(
          { mode: "visible", children: primaryChildren },
          workInProgress2.mode
        );
        primaryChildren.return = workInProgress2;
        return workInProgress2.child = primaryChildren;
      }
      function mountWorkInProgressOffscreenFiber(offscreenProps, mode) {
        offscreenProps = createFiberImplClass(22, offscreenProps, null, mode);
        offscreenProps.lanes = 0;
        return offscreenProps;
      }
      function retrySuspenseComponentWithoutHydrating(current, workInProgress2, renderLanes2) {
        reconcileChildFibers(workInProgress2, current.child, null, renderLanes2);
        current = mountSuspensePrimaryChildren(
          workInProgress2,
          workInProgress2.pendingProps.children
        );
        current.flags |= 2;
        workInProgress2.memoizedState = null;
        return current;
      }
      function scheduleSuspenseWorkOnFiber(fiber, renderLanes2, propagationRoot) {
        fiber.lanes |= renderLanes2;
        var alternate = fiber.alternate;
        null !== alternate && (alternate.lanes |= renderLanes2);
        scheduleContextWorkOnParentPath(fiber.return, renderLanes2, propagationRoot);
      }
      function initSuspenseListRenderState(workInProgress2, isBackwards, tail, lastContentRow, tailMode, treeForkCount2) {
        var renderState = workInProgress2.memoizedState;
        null === renderState ? workInProgress2.memoizedState = {
          isBackwards,
          rendering: null,
          renderingStartTime: 0,
          last: lastContentRow,
          tail,
          tailMode,
          treeForkCount: treeForkCount2
        } : (renderState.isBackwards = isBackwards, renderState.rendering = null, renderState.renderingStartTime = 0, renderState.last = lastContentRow, renderState.tail = tail, renderState.tailMode = tailMode, renderState.treeForkCount = treeForkCount2);
      }
      function updateSuspenseListComponent(current, workInProgress2, renderLanes2) {
        var nextProps = workInProgress2.pendingProps, revealOrder = nextProps.revealOrder, tailMode = nextProps.tail;
        nextProps = nextProps.children;
        var suspenseContext = suspenseStackCursor.current, shouldForceFallback = 0 !== (suspenseContext & 2);
        shouldForceFallback ? (suspenseContext = suspenseContext & 1 | 2, workInProgress2.flags |= 128) : suspenseContext &= 1;
        push(suspenseStackCursor, suspenseContext);
        reconcileChildren(current, workInProgress2, nextProps, renderLanes2);
        nextProps = isHydrating ? treeForkCount : 0;
        if (!shouldForceFallback && null !== current && 0 !== (current.flags & 128))
          a: for (current = workInProgress2.child; null !== current; ) {
            if (13 === current.tag)
              null !== current.memoizedState && scheduleSuspenseWorkOnFiber(current, renderLanes2, workInProgress2);
            else if (19 === current.tag)
              scheduleSuspenseWorkOnFiber(current, renderLanes2, workInProgress2);
            else if (null !== current.child) {
              current.child.return = current;
              current = current.child;
              continue;
            }
            if (current === workInProgress2) break a;
            for (; null === current.sibling; ) {
              if (null === current.return || current.return === workInProgress2)
                break a;
              current = current.return;
            }
            current.sibling.return = current.return;
            current = current.sibling;
          }
        switch (revealOrder) {
          case "forwards":
            renderLanes2 = workInProgress2.child;
            for (revealOrder = null; null !== renderLanes2; )
              current = renderLanes2.alternate, null !== current && null === findFirstSuspended(current) && (revealOrder = renderLanes2), renderLanes2 = renderLanes2.sibling;
            renderLanes2 = revealOrder;
            null === renderLanes2 ? (revealOrder = workInProgress2.child, workInProgress2.child = null) : (revealOrder = renderLanes2.sibling, renderLanes2.sibling = null);
            initSuspenseListRenderState(
              workInProgress2,
              false,
              revealOrder,
              renderLanes2,
              tailMode,
              nextProps
            );
            break;
          case "backwards":
          case "unstable_legacy-backwards":
            renderLanes2 = null;
            revealOrder = workInProgress2.child;
            for (workInProgress2.child = null; null !== revealOrder; ) {
              current = revealOrder.alternate;
              if (null !== current && null === findFirstSuspended(current)) {
                workInProgress2.child = revealOrder;
                break;
              }
              current = revealOrder.sibling;
              revealOrder.sibling = renderLanes2;
              renderLanes2 = revealOrder;
              revealOrder = current;
            }
            initSuspenseListRenderState(
              workInProgress2,
              true,
              renderLanes2,
              null,
              tailMode,
              nextProps
            );
            break;
          case "together":
            initSuspenseListRenderState(
              workInProgress2,
              false,
              null,
              null,
              void 0,
              nextProps
            );
            break;
          default:
            workInProgress2.memoizedState = null;
        }
        return workInProgress2.child;
      }
      function bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2) {
        null !== current && (workInProgress2.dependencies = current.dependencies);
        workInProgressRootSkippedLanes |= workInProgress2.lanes;
        if (0 === (renderLanes2 & workInProgress2.childLanes))
          if (null !== current) {
            if (propagateParentContextChanges(
              current,
              workInProgress2,
              renderLanes2,
              false
            ), 0 === (renderLanes2 & workInProgress2.childLanes))
              return null;
          } else return null;
        if (null !== current && workInProgress2.child !== current.child)
          throw Error(formatProdErrorMessage(153));
        if (null !== workInProgress2.child) {
          current = workInProgress2.child;
          renderLanes2 = createWorkInProgress(current, current.pendingProps);
          workInProgress2.child = renderLanes2;
          for (renderLanes2.return = workInProgress2; null !== current.sibling; )
            current = current.sibling, renderLanes2 = renderLanes2.sibling = createWorkInProgress(current, current.pendingProps), renderLanes2.return = workInProgress2;
          renderLanes2.sibling = null;
        }
        return workInProgress2.child;
      }
      function checkScheduledUpdateOrContext(current, renderLanes2) {
        if (0 !== (current.lanes & renderLanes2)) return true;
        current = current.dependencies;
        return null !== current && checkIfContextChanged(current) ? true : false;
      }
      function attemptEarlyBailoutIfNoScheduledUpdate(current, workInProgress2, renderLanes2) {
        switch (workInProgress2.tag) {
          case 3:
            pushHostContainer(workInProgress2, workInProgress2.stateNode.containerInfo);
            pushProvider(workInProgress2, CacheContext, current.memoizedState.cache);
            resetHydrationState();
            break;
          case 27:
          case 5:
            pushHostContext(workInProgress2);
            break;
          case 4:
            pushHostContainer(workInProgress2, workInProgress2.stateNode.containerInfo);
            break;
          case 10:
            pushProvider(
              workInProgress2,
              workInProgress2.type,
              workInProgress2.memoizedProps.value
            );
            break;
          case 31:
            if (null !== workInProgress2.memoizedState)
              return workInProgress2.flags |= 128, pushDehydratedActivitySuspenseHandler(workInProgress2), null;
            break;
          case 13:
            var state$102 = workInProgress2.memoizedState;
            if (null !== state$102) {
              if (null !== state$102.dehydrated)
                return pushPrimaryTreeSuspenseHandler(workInProgress2), workInProgress2.flags |= 128, null;
              if (0 !== (renderLanes2 & workInProgress2.child.childLanes))
                return updateSuspenseComponent(current, workInProgress2, renderLanes2);
              pushPrimaryTreeSuspenseHandler(workInProgress2);
              current = bailoutOnAlreadyFinishedWork(
                current,
                workInProgress2,
                renderLanes2
              );
              return null !== current ? current.sibling : null;
            }
            pushPrimaryTreeSuspenseHandler(workInProgress2);
            break;
          case 19:
            var didSuspendBefore = 0 !== (current.flags & 128);
            state$102 = 0 !== (renderLanes2 & workInProgress2.childLanes);
            state$102 || (propagateParentContextChanges(
              current,
              workInProgress2,
              renderLanes2,
              false
            ), state$102 = 0 !== (renderLanes2 & workInProgress2.childLanes));
            if (didSuspendBefore) {
              if (state$102)
                return updateSuspenseListComponent(
                  current,
                  workInProgress2,
                  renderLanes2
                );
              workInProgress2.flags |= 128;
            }
            didSuspendBefore = workInProgress2.memoizedState;
            null !== didSuspendBefore && (didSuspendBefore.rendering = null, didSuspendBefore.tail = null, didSuspendBefore.lastEffect = null);
            push(suspenseStackCursor, suspenseStackCursor.current);
            if (state$102) break;
            else return null;
          case 22:
            return workInProgress2.lanes = 0, updateOffscreenComponent(
              current,
              workInProgress2,
              renderLanes2,
              workInProgress2.pendingProps
            );
          case 24:
            pushProvider(workInProgress2, CacheContext, current.memoizedState.cache);
        }
        return bailoutOnAlreadyFinishedWork(current, workInProgress2, renderLanes2);
      }
      function beginWork(current, workInProgress2, renderLanes2) {
        if (null !== current)
          if (current.memoizedProps !== workInProgress2.pendingProps)
            didReceiveUpdate = true;
          else {
            if (!checkScheduledUpdateOrContext(current, renderLanes2) && 0 === (workInProgress2.flags & 128))
              return didReceiveUpdate = false, attemptEarlyBailoutIfNoScheduledUpdate(
                current,
                workInProgress2,
                renderLanes2
              );
            didReceiveUpdate = 0 !== (current.flags & 131072) ? true : false;
          }
        else
          didReceiveUpdate = false, isHydrating && 0 !== (workInProgress2.flags & 1048576) && pushTreeId(workInProgress2, treeForkCount, workInProgress2.index);
        workInProgress2.lanes = 0;
        switch (workInProgress2.tag) {
          case 16:
            a: {
              var props = workInProgress2.pendingProps;
              current = resolveLazy(workInProgress2.elementType);
              workInProgress2.type = current;
              if ("function" === typeof current)
                shouldConstruct(current) ? (props = resolveClassComponentProps(current, props), workInProgress2.tag = 1, workInProgress2 = updateClassComponent(
                  null,
                  workInProgress2,
                  current,
                  props,
                  renderLanes2
                )) : (workInProgress2.tag = 0, workInProgress2 = updateFunctionComponent(
                  null,
                  workInProgress2,
                  current,
                  props,
                  renderLanes2
                ));
              else {
                if (void 0 !== current && null !== current) {
                  var $$typeof = current.$$typeof;
                  if ($$typeof === REACT_FORWARD_REF_TYPE) {
                    workInProgress2.tag = 11;
                    workInProgress2 = updateForwardRef(
                      null,
                      workInProgress2,
                      current,
                      props,
                      renderLanes2
                    );
                    break a;
                  } else if ($$typeof === REACT_MEMO_TYPE) {
                    workInProgress2.tag = 14;
                    workInProgress2 = updateMemoComponent(
                      null,
                      workInProgress2,
                      current,
                      props,
                      renderLanes2
                    );
                    break a;
                  }
                }
                workInProgress2 = getComponentNameFromType(current) || current;
                throw Error(formatProdErrorMessage(306, workInProgress2, ""));
              }
            }
            return workInProgress2;
          case 0:
            return updateFunctionComponent(
              current,
              workInProgress2,
              workInProgress2.type,
              workInProgress2.pendingProps,
              renderLanes2
            );
          case 1:
            return props = workInProgress2.type, $$typeof = resolveClassComponentProps(
              props,
              workInProgress2.pendingProps
            ), updateClassComponent(
              current,
              workInProgress2,
              props,
              $$typeof,
              renderLanes2
            );
          case 3:
            a: {
              pushHostContainer(
                workInProgress2,
                workInProgress2.stateNode.containerInfo
              );
              if (null === current) throw Error(formatProdErrorMessage(387));
              props = workInProgress2.pendingProps;
              var prevState = workInProgress2.memoizedState;
              $$typeof = prevState.element;
              cloneUpdateQueue(current, workInProgress2);
              processUpdateQueue(workInProgress2, props, null, renderLanes2);
              var nextState = workInProgress2.memoizedState;
              props = nextState.cache;
              pushProvider(workInProgress2, CacheContext, props);
              props !== prevState.cache && propagateContextChanges(
                workInProgress2,
                [CacheContext],
                renderLanes2,
                true
              );
              suspendIfUpdateReadFromEntangledAsyncAction();
              props = nextState.element;
              if (prevState.isDehydrated)
                if (prevState = {
                  element: props,
                  isDehydrated: false,
                  cache: nextState.cache
                }, workInProgress2.updateQueue.baseState = prevState, workInProgress2.memoizedState = prevState, workInProgress2.flags & 256) {
                  workInProgress2 = mountHostRootWithoutHydrating(
                    current,
                    workInProgress2,
                    props,
                    renderLanes2
                  );
                  break a;
                } else if (props !== $$typeof) {
                  $$typeof = createCapturedValueAtFiber(
                    Error(formatProdErrorMessage(424)),
                    workInProgress2
                  );
                  queueHydrationError($$typeof);
                  workInProgress2 = mountHostRootWithoutHydrating(
                    current,
                    workInProgress2,
                    props,
                    renderLanes2
                  );
                  break a;
                } else {
                  current = workInProgress2.stateNode.containerInfo;
                  switch (current.nodeType) {
                    case 9:
                      current = current.body;
                      break;
                    default:
                      current = "HTML" === current.nodeName ? current.ownerDocument.body : current;
                  }
                  nextHydratableInstance = getNextHydratable(current.firstChild);
                  hydrationParentFiber = workInProgress2;
                  isHydrating = true;
                  hydrationErrors = null;
                  rootOrSingletonContext = true;
                  renderLanes2 = mountChildFibers(
                    workInProgress2,
                    null,
                    props,
                    renderLanes2
                  );
                  for (workInProgress2.child = renderLanes2; renderLanes2; )
                    renderLanes2.flags = renderLanes2.flags & -3 | 4096, renderLanes2 = renderLanes2.sibling;
                }
              else {
                resetHydrationState();
                if (props === $$typeof) {
                  workInProgress2 = bailoutOnAlreadyFinishedWork(
                    current,
                    workInProgress2,
                    renderLanes2
                  );
                  break a;
                }
                reconcileChildren(current, workInProgress2, props, renderLanes2);
              }
              workInProgress2 = workInProgress2.child;
            }
            return workInProgress2;
          case 26:
            return markRef(current, workInProgress2), null === current ? (renderLanes2 = getResource(
              workInProgress2.type,
              null,
              workInProgress2.pendingProps,
              null
            )) ? workInProgress2.memoizedState = renderLanes2 : isHydrating || (renderLanes2 = workInProgress2.type, current = workInProgress2.pendingProps, props = getOwnerDocumentFromRootContainer(
              rootInstanceStackCursor.current
            ).createElement(renderLanes2), props[internalInstanceKey] = workInProgress2, props[internalPropsKey] = current, setInitialProperties(props, renderLanes2, current), markNodeAsHoistable(props), workInProgress2.stateNode = props) : workInProgress2.memoizedState = getResource(
              workInProgress2.type,
              current.memoizedProps,
              workInProgress2.pendingProps,
              current.memoizedState
            ), null;
          case 27:
            return pushHostContext(workInProgress2), null === current && isHydrating && (props = workInProgress2.stateNode = resolveSingletonInstance(
              workInProgress2.type,
              workInProgress2.pendingProps,
              rootInstanceStackCursor.current
            ), hydrationParentFiber = workInProgress2, rootOrSingletonContext = true, $$typeof = nextHydratableInstance, isSingletonScope(workInProgress2.type) ? (previousHydratableOnEnteringScopedSingleton = $$typeof, nextHydratableInstance = getNextHydratable(props.firstChild)) : nextHydratableInstance = $$typeof), reconcileChildren(
              current,
              workInProgress2,
              workInProgress2.pendingProps.children,
              renderLanes2
            ), markRef(current, workInProgress2), null === current && (workInProgress2.flags |= 4194304), workInProgress2.child;
          case 5:
            if (null === current && isHydrating) {
              if ($$typeof = props = nextHydratableInstance)
                props = canHydrateInstance(
                  props,
                  workInProgress2.type,
                  workInProgress2.pendingProps,
                  rootOrSingletonContext
                ), null !== props ? (workInProgress2.stateNode = props, hydrationParentFiber = workInProgress2, nextHydratableInstance = getNextHydratable(props.firstChild), rootOrSingletonContext = false, $$typeof = true) : $$typeof = false;
              $$typeof || throwOnHydrationMismatch(workInProgress2);
            }
            pushHostContext(workInProgress2);
            $$typeof = workInProgress2.type;
            prevState = workInProgress2.pendingProps;
            nextState = null !== current ? current.memoizedProps : null;
            props = prevState.children;
            shouldSetTextContent($$typeof, prevState) ? props = null : null !== nextState && shouldSetTextContent($$typeof, nextState) && (workInProgress2.flags |= 32);
            null !== workInProgress2.memoizedState && ($$typeof = renderWithHooks(
              current,
              workInProgress2,
              TransitionAwareHostComponent,
              null,
              null,
              renderLanes2
            ), HostTransitionContext._currentValue = $$typeof);
            markRef(current, workInProgress2);
            reconcileChildren(current, workInProgress2, props, renderLanes2);
            return workInProgress2.child;
          case 6:
            if (null === current && isHydrating) {
              if (current = renderLanes2 = nextHydratableInstance)
                renderLanes2 = canHydrateTextInstance(
                  renderLanes2,
                  workInProgress2.pendingProps,
                  rootOrSingletonContext
                ), null !== renderLanes2 ? (workInProgress2.stateNode = renderLanes2, hydrationParentFiber = workInProgress2, nextHydratableInstance = null, current = true) : current = false;
              current || throwOnHydrationMismatch(workInProgress2);
            }
            return null;
          case 13:
            return updateSuspenseComponent(current, workInProgress2, renderLanes2);
          case 4:
            return pushHostContainer(
              workInProgress2,
              workInProgress2.stateNode.containerInfo
            ), props = workInProgress2.pendingProps, null === current ? workInProgress2.child = reconcileChildFibers(
              workInProgress2,
              null,
              props,
              renderLanes2
            ) : reconcileChildren(current, workInProgress2, props, renderLanes2), workInProgress2.child;
          case 11:
            return updateForwardRef(
              current,
              workInProgress2,
              workInProgress2.type,
              workInProgress2.pendingProps,
              renderLanes2
            );
          case 7:
            return reconcileChildren(
              current,
              workInProgress2,
              workInProgress2.pendingProps,
              renderLanes2
            ), workInProgress2.child;
          case 8:
            return reconcileChildren(
              current,
              workInProgress2,
              workInProgress2.pendingProps.children,
              renderLanes2
            ), workInProgress2.child;
          case 12:
            return reconcileChildren(
              current,
              workInProgress2,
              workInProgress2.pendingProps.children,
              renderLanes2
            ), workInProgress2.child;
          case 10:
            return props = workInProgress2.pendingProps, pushProvider(workInProgress2, workInProgress2.type, props.value), reconcileChildren(current, workInProgress2, props.children, renderLanes2), workInProgress2.child;
          case 9:
            return $$typeof = workInProgress2.type._context, props = workInProgress2.pendingProps.children, prepareToReadContext(workInProgress2), $$typeof = readContext($$typeof), props = props($$typeof), workInProgress2.flags |= 1, reconcileChildren(current, workInProgress2, props, renderLanes2), workInProgress2.child;
          case 14:
            return updateMemoComponent(
              current,
              workInProgress2,
              workInProgress2.type,
              workInProgress2.pendingProps,
              renderLanes2
            );
          case 15:
            return updateSimpleMemoComponent(
              current,
              workInProgress2,
              workInProgress2.type,
              workInProgress2.pendingProps,
              renderLanes2
            );
          case 19:
            return updateSuspenseListComponent(current, workInProgress2, renderLanes2);
          case 31:
            return updateActivityComponent(current, workInProgress2, renderLanes2);
          case 22:
            return updateOffscreenComponent(
              current,
              workInProgress2,
              renderLanes2,
              workInProgress2.pendingProps
            );
          case 24:
            return prepareToReadContext(workInProgress2), props = readContext(CacheContext), null === current ? ($$typeof = peekCacheFromPool(), null === $$typeof && ($$typeof = workInProgressRoot, prevState = createCache(), $$typeof.pooledCache = prevState, prevState.refCount++, null !== prevState && ($$typeof.pooledCacheLanes |= renderLanes2), $$typeof = prevState), workInProgress2.memoizedState = { parent: props, cache: $$typeof }, initializeUpdateQueue(workInProgress2), pushProvider(workInProgress2, CacheContext, $$typeof)) : (0 !== (current.lanes & renderLanes2) && (cloneUpdateQueue(current, workInProgress2), processUpdateQueue(workInProgress2, null, null, renderLanes2), suspendIfUpdateReadFromEntangledAsyncAction()), $$typeof = current.memoizedState, prevState = workInProgress2.memoizedState, $$typeof.parent !== props ? ($$typeof = { parent: props, cache: props }, workInProgress2.memoizedState = $$typeof, 0 === workInProgress2.lanes && (workInProgress2.memoizedState = workInProgress2.updateQueue.baseState = $$typeof), pushProvider(workInProgress2, CacheContext, props)) : (props = prevState.cache, pushProvider(workInProgress2, CacheContext, props), props !== $$typeof.cache && propagateContextChanges(
              workInProgress2,
              [CacheContext],
              renderLanes2,
              true
            ))), reconcileChildren(
              current,
              workInProgress2,
              workInProgress2.pendingProps.children,
              renderLanes2
            ), workInProgress2.child;
          case 29:
            throw workInProgress2.pendingProps;
        }
        throw Error(formatProdErrorMessage(156, workInProgress2.tag));
      }
      function markUpdate(workInProgress2) {
        workInProgress2.flags |= 4;
      }
      function preloadInstanceAndSuspendIfNeeded(workInProgress2, type, oldProps, newProps, renderLanes2) {
        if (type = 0 !== (workInProgress2.mode & 32)) type = false;
        if (type) {
          if (workInProgress2.flags |= 16777216, (renderLanes2 & 335544128) === renderLanes2)
            if (workInProgress2.stateNode.complete) workInProgress2.flags |= 8192;
            else if (shouldRemainOnPreviousScreen()) workInProgress2.flags |= 8192;
            else
              throw suspendedThenable = noopSuspenseyCommitThenable, SuspenseyCommitException;
        } else workInProgress2.flags &= -16777217;
      }
      function preloadResourceAndSuspendIfNeeded(workInProgress2, resource) {
        if ("stylesheet" !== resource.type || 0 !== (resource.state.loading & 4))
          workInProgress2.flags &= -16777217;
        else if (workInProgress2.flags |= 16777216, !preloadResource(resource))
          if (shouldRemainOnPreviousScreen()) workInProgress2.flags |= 8192;
          else
            throw suspendedThenable = noopSuspenseyCommitThenable, SuspenseyCommitException;
      }
      function scheduleRetryEffect(workInProgress2, retryQueue) {
        null !== retryQueue && (workInProgress2.flags |= 4);
        workInProgress2.flags & 16384 && (retryQueue = 22 !== workInProgress2.tag ? claimNextRetryLane() : 536870912, workInProgress2.lanes |= retryQueue, workInProgressSuspendedRetryLanes |= retryQueue);
      }
      function cutOffTailIfNeeded(renderState, hasRenderedATailFallback) {
        if (!isHydrating)
          switch (renderState.tailMode) {
            case "hidden":
              hasRenderedATailFallback = renderState.tail;
              for (var lastTailNode = null; null !== hasRenderedATailFallback; )
                null !== hasRenderedATailFallback.alternate && (lastTailNode = hasRenderedATailFallback), hasRenderedATailFallback = hasRenderedATailFallback.sibling;
              null === lastTailNode ? renderState.tail = null : lastTailNode.sibling = null;
              break;
            case "collapsed":
              lastTailNode = renderState.tail;
              for (var lastTailNode$106 = null; null !== lastTailNode; )
                null !== lastTailNode.alternate && (lastTailNode$106 = lastTailNode), lastTailNode = lastTailNode.sibling;
              null === lastTailNode$106 ? hasRenderedATailFallback || null === renderState.tail ? renderState.tail = null : renderState.tail.sibling = null : lastTailNode$106.sibling = null;
          }
      }
      function bubbleProperties(completedWork) {
        var didBailout = null !== completedWork.alternate && completedWork.alternate.child === completedWork.child, newChildLanes = 0, subtreeFlags = 0;
        if (didBailout)
          for (var child$107 = completedWork.child; null !== child$107; )
            newChildLanes |= child$107.lanes | child$107.childLanes, subtreeFlags |= child$107.subtreeFlags & 65011712, subtreeFlags |= child$107.flags & 65011712, child$107.return = completedWork, child$107 = child$107.sibling;
        else
          for (child$107 = completedWork.child; null !== child$107; )
            newChildLanes |= child$107.lanes | child$107.childLanes, subtreeFlags |= child$107.subtreeFlags, subtreeFlags |= child$107.flags, child$107.return = completedWork, child$107 = child$107.sibling;
        completedWork.subtreeFlags |= subtreeFlags;
        completedWork.childLanes = newChildLanes;
        return didBailout;
      }
      function completeWork(current, workInProgress2, renderLanes2) {
        var newProps = workInProgress2.pendingProps;
        popTreeContext(workInProgress2);
        switch (workInProgress2.tag) {
          case 16:
          case 15:
          case 0:
          case 11:
          case 7:
          case 8:
          case 12:
          case 9:
          case 14:
            return bubbleProperties(workInProgress2), null;
          case 1:
            return bubbleProperties(workInProgress2), null;
          case 3:
            renderLanes2 = workInProgress2.stateNode;
            newProps = null;
            null !== current && (newProps = current.memoizedState.cache);
            workInProgress2.memoizedState.cache !== newProps && (workInProgress2.flags |= 2048);
            popProvider(CacheContext);
            popHostContainer();
            renderLanes2.pendingContext && (renderLanes2.context = renderLanes2.pendingContext, renderLanes2.pendingContext = null);
            if (null === current || null === current.child)
              popHydrationState(workInProgress2) ? markUpdate(workInProgress2) : null === current || current.memoizedState.isDehydrated && 0 === (workInProgress2.flags & 256) || (workInProgress2.flags |= 1024, upgradeHydrationErrorsToRecoverable());
            bubbleProperties(workInProgress2);
            return null;
          case 26:
            var type = workInProgress2.type, nextResource = workInProgress2.memoizedState;
            null === current ? (markUpdate(workInProgress2), null !== nextResource ? (bubbleProperties(workInProgress2), preloadResourceAndSuspendIfNeeded(workInProgress2, nextResource)) : (bubbleProperties(workInProgress2), preloadInstanceAndSuspendIfNeeded(
              workInProgress2,
              type,
              null,
              newProps,
              renderLanes2
            ))) : nextResource ? nextResource !== current.memoizedState ? (markUpdate(workInProgress2), bubbleProperties(workInProgress2), preloadResourceAndSuspendIfNeeded(workInProgress2, nextResource)) : (bubbleProperties(workInProgress2), workInProgress2.flags &= -16777217) : (current = current.memoizedProps, current !== newProps && markUpdate(workInProgress2), bubbleProperties(workInProgress2), preloadInstanceAndSuspendIfNeeded(
              workInProgress2,
              type,
              current,
              newProps,
              renderLanes2
            ));
            return null;
          case 27:
            popHostContext(workInProgress2);
            renderLanes2 = rootInstanceStackCursor.current;
            type = workInProgress2.type;
            if (null !== current && null != workInProgress2.stateNode)
              current.memoizedProps !== newProps && markUpdate(workInProgress2);
            else {
              if (!newProps) {
                if (null === workInProgress2.stateNode)
                  throw Error(formatProdErrorMessage(166));
                bubbleProperties(workInProgress2);
                return null;
              }
              current = contextStackCursor.current;
              popHydrationState(workInProgress2) ? prepareToHydrateHostInstance(workInProgress2, current) : (current = resolveSingletonInstance(type, newProps, renderLanes2), workInProgress2.stateNode = current, markUpdate(workInProgress2));
            }
            bubbleProperties(workInProgress2);
            return null;
          case 5:
            popHostContext(workInProgress2);
            type = workInProgress2.type;
            if (null !== current && null != workInProgress2.stateNode)
              current.memoizedProps !== newProps && markUpdate(workInProgress2);
            else {
              if (!newProps) {
                if (null === workInProgress2.stateNode)
                  throw Error(formatProdErrorMessage(166));
                bubbleProperties(workInProgress2);
                return null;
              }
              nextResource = contextStackCursor.current;
              if (popHydrationState(workInProgress2))
                prepareToHydrateHostInstance(workInProgress2, nextResource);
              else {
                var ownerDocument = getOwnerDocumentFromRootContainer(
                  rootInstanceStackCursor.current
                );
                switch (nextResource) {
                  case 1:
                    nextResource = ownerDocument.createElementNS(
                      "http://www.w3.org/2000/svg",
                      type
                    );
                    break;
                  case 2:
                    nextResource = ownerDocument.createElementNS(
                      "http://www.w3.org/1998/Math/MathML",
                      type
                    );
                    break;
                  default:
                    switch (type) {
                      case "svg":
                        nextResource = ownerDocument.createElementNS(
                          "http://www.w3.org/2000/svg",
                          type
                        );
                        break;
                      case "math":
                        nextResource = ownerDocument.createElementNS(
                          "http://www.w3.org/1998/Math/MathML",
                          type
                        );
                        break;
                      case "script":
                        nextResource = ownerDocument.createElement("div");
                        nextResource.innerHTML = "<script><\/script>";
                        nextResource = nextResource.removeChild(
                          nextResource.firstChild
                        );
                        break;
                      case "select":
                        nextResource = "string" === typeof newProps.is ? ownerDocument.createElement("select", {
                          is: newProps.is
                        }) : ownerDocument.createElement("select");
                        newProps.multiple ? nextResource.multiple = true : newProps.size && (nextResource.size = newProps.size);
                        break;
                      default:
                        nextResource = "string" === typeof newProps.is ? ownerDocument.createElement(type, { is: newProps.is }) : ownerDocument.createElement(type);
                    }
                }
                nextResource[internalInstanceKey] = workInProgress2;
                nextResource[internalPropsKey] = newProps;
                a: for (ownerDocument = workInProgress2.child; null !== ownerDocument; ) {
                  if (5 === ownerDocument.tag || 6 === ownerDocument.tag)
                    nextResource.appendChild(ownerDocument.stateNode);
                  else if (4 !== ownerDocument.tag && 27 !== ownerDocument.tag && null !== ownerDocument.child) {
                    ownerDocument.child.return = ownerDocument;
                    ownerDocument = ownerDocument.child;
                    continue;
                  }
                  if (ownerDocument === workInProgress2) break a;
                  for (; null === ownerDocument.sibling; ) {
                    if (null === ownerDocument.return || ownerDocument.return === workInProgress2)
                      break a;
                    ownerDocument = ownerDocument.return;
                  }
                  ownerDocument.sibling.return = ownerDocument.return;
                  ownerDocument = ownerDocument.sibling;
                }
                workInProgress2.stateNode = nextResource;
                a: switch (setInitialProperties(nextResource, type, newProps), type) {
                  case "button":
                  case "input":
                  case "select":
                  case "textarea":
                    newProps = !!newProps.autoFocus;
                    break a;
                  case "img":
                    newProps = true;
                    break a;
                  default:
                    newProps = false;
                }
                newProps && markUpdate(workInProgress2);
              }
            }
            bubbleProperties(workInProgress2);
            preloadInstanceAndSuspendIfNeeded(
              workInProgress2,
              workInProgress2.type,
              null === current ? null : current.memoizedProps,
              workInProgress2.pendingProps,
              renderLanes2
            );
            return null;
          case 6:
            if (current && null != workInProgress2.stateNode)
              current.memoizedProps !== newProps && markUpdate(workInProgress2);
            else {
              if ("string" !== typeof newProps && null === workInProgress2.stateNode)
                throw Error(formatProdErrorMessage(166));
              current = rootInstanceStackCursor.current;
              if (popHydrationState(workInProgress2)) {
                current = workInProgress2.stateNode;
                renderLanes2 = workInProgress2.memoizedProps;
                newProps = null;
                type = hydrationParentFiber;
                if (null !== type)
                  switch (type.tag) {
                    case 27:
                    case 5:
                      newProps = type.memoizedProps;
                  }
                current[internalInstanceKey] = workInProgress2;
                current = current.nodeValue === renderLanes2 || null !== newProps && true === newProps.suppressHydrationWarning || checkForUnmatchedText(current.nodeValue, renderLanes2) ? true : false;
                current || throwOnHydrationMismatch(workInProgress2, true);
              } else
                current = getOwnerDocumentFromRootContainer(current).createTextNode(
                  newProps
                ), current[internalInstanceKey] = workInProgress2, workInProgress2.stateNode = current;
            }
            bubbleProperties(workInProgress2);
            return null;
          case 31:
            renderLanes2 = workInProgress2.memoizedState;
            if (null === current || null !== current.memoizedState) {
              newProps = popHydrationState(workInProgress2);
              if (null !== renderLanes2) {
                if (null === current) {
                  if (!newProps) throw Error(formatProdErrorMessage(318));
                  current = workInProgress2.memoizedState;
                  current = null !== current ? current.dehydrated : null;
                  if (!current) throw Error(formatProdErrorMessage(557));
                  current[internalInstanceKey] = workInProgress2;
                } else
                  resetHydrationState(), 0 === (workInProgress2.flags & 128) && (workInProgress2.memoizedState = null), workInProgress2.flags |= 4;
                bubbleProperties(workInProgress2);
                current = false;
              } else
                renderLanes2 = upgradeHydrationErrorsToRecoverable(), null !== current && null !== current.memoizedState && (current.memoizedState.hydrationErrors = renderLanes2), current = true;
              if (!current) {
                if (workInProgress2.flags & 256)
                  return popSuspenseHandler(workInProgress2), workInProgress2;
                popSuspenseHandler(workInProgress2);
                return null;
              }
              if (0 !== (workInProgress2.flags & 128))
                throw Error(formatProdErrorMessage(558));
            }
            bubbleProperties(workInProgress2);
            return null;
          case 13:
            newProps = workInProgress2.memoizedState;
            if (null === current || null !== current.memoizedState && null !== current.memoizedState.dehydrated) {
              type = popHydrationState(workInProgress2);
              if (null !== newProps && null !== newProps.dehydrated) {
                if (null === current) {
                  if (!type) throw Error(formatProdErrorMessage(318));
                  type = workInProgress2.memoizedState;
                  type = null !== type ? type.dehydrated : null;
                  if (!type) throw Error(formatProdErrorMessage(317));
                  type[internalInstanceKey] = workInProgress2;
                } else
                  resetHydrationState(), 0 === (workInProgress2.flags & 128) && (workInProgress2.memoizedState = null), workInProgress2.flags |= 4;
                bubbleProperties(workInProgress2);
                type = false;
              } else
                type = upgradeHydrationErrorsToRecoverable(), null !== current && null !== current.memoizedState && (current.memoizedState.hydrationErrors = type), type = true;
              if (!type) {
                if (workInProgress2.flags & 256)
                  return popSuspenseHandler(workInProgress2), workInProgress2;
                popSuspenseHandler(workInProgress2);
                return null;
              }
            }
            popSuspenseHandler(workInProgress2);
            if (0 !== (workInProgress2.flags & 128))
              return workInProgress2.lanes = renderLanes2, workInProgress2;
            renderLanes2 = null !== newProps;
            current = null !== current && null !== current.memoizedState;
            renderLanes2 && (newProps = workInProgress2.child, type = null, null !== newProps.alternate && null !== newProps.alternate.memoizedState && null !== newProps.alternate.memoizedState.cachePool && (type = newProps.alternate.memoizedState.cachePool.pool), nextResource = null, null !== newProps.memoizedState && null !== newProps.memoizedState.cachePool && (nextResource = newProps.memoizedState.cachePool.pool), nextResource !== type && (newProps.flags |= 2048));
            renderLanes2 !== current && renderLanes2 && (workInProgress2.child.flags |= 8192);
            scheduleRetryEffect(workInProgress2, workInProgress2.updateQueue);
            bubbleProperties(workInProgress2);
            return null;
          case 4:
            return popHostContainer(), null === current && listenToAllSupportedEvents(workInProgress2.stateNode.containerInfo), bubbleProperties(workInProgress2), null;
          case 10:
            return popProvider(workInProgress2.type), bubbleProperties(workInProgress2), null;
          case 19:
            pop(suspenseStackCursor);
            newProps = workInProgress2.memoizedState;
            if (null === newProps) return bubbleProperties(workInProgress2), null;
            type = 0 !== (workInProgress2.flags & 128);
            nextResource = newProps.rendering;
            if (null === nextResource)
              if (type) cutOffTailIfNeeded(newProps, false);
              else {
                if (0 !== workInProgressRootExitStatus || null !== current && 0 !== (current.flags & 128))
                  for (current = workInProgress2.child; null !== current; ) {
                    nextResource = findFirstSuspended(current);
                    if (null !== nextResource) {
                      workInProgress2.flags |= 128;
                      cutOffTailIfNeeded(newProps, false);
                      current = nextResource.updateQueue;
                      workInProgress2.updateQueue = current;
                      scheduleRetryEffect(workInProgress2, current);
                      workInProgress2.subtreeFlags = 0;
                      current = renderLanes2;
                      for (renderLanes2 = workInProgress2.child; null !== renderLanes2; )
                        resetWorkInProgress(renderLanes2, current), renderLanes2 = renderLanes2.sibling;
                      push(
                        suspenseStackCursor,
                        suspenseStackCursor.current & 1 | 2
                      );
                      isHydrating && pushTreeFork(workInProgress2, newProps.treeForkCount);
                      return workInProgress2.child;
                    }
                    current = current.sibling;
                  }
                null !== newProps.tail && now() > workInProgressRootRenderTargetTime && (workInProgress2.flags |= 128, type = true, cutOffTailIfNeeded(newProps, false), workInProgress2.lanes = 4194304);
              }
            else {
              if (!type)
                if (current = findFirstSuspended(nextResource), null !== current) {
                  if (workInProgress2.flags |= 128, type = true, current = current.updateQueue, workInProgress2.updateQueue = current, scheduleRetryEffect(workInProgress2, current), cutOffTailIfNeeded(newProps, true), null === newProps.tail && "hidden" === newProps.tailMode && !nextResource.alternate && !isHydrating)
                    return bubbleProperties(workInProgress2), null;
                } else
                  2 * now() - newProps.renderingStartTime > workInProgressRootRenderTargetTime && 536870912 !== renderLanes2 && (workInProgress2.flags |= 128, type = true, cutOffTailIfNeeded(newProps, false), workInProgress2.lanes = 4194304);
              newProps.isBackwards ? (nextResource.sibling = workInProgress2.child, workInProgress2.child = nextResource) : (current = newProps.last, null !== current ? current.sibling = nextResource : workInProgress2.child = nextResource, newProps.last = nextResource);
            }
            if (null !== newProps.tail)
              return current = newProps.tail, newProps.rendering = current, newProps.tail = current.sibling, newProps.renderingStartTime = now(), current.sibling = null, renderLanes2 = suspenseStackCursor.current, push(
                suspenseStackCursor,
                type ? renderLanes2 & 1 | 2 : renderLanes2 & 1
              ), isHydrating && pushTreeFork(workInProgress2, newProps.treeForkCount), current;
            bubbleProperties(workInProgress2);
            return null;
          case 22:
          case 23:
            return popSuspenseHandler(workInProgress2), popHiddenContext(), newProps = null !== workInProgress2.memoizedState, null !== current ? null !== current.memoizedState !== newProps && (workInProgress2.flags |= 8192) : newProps && (workInProgress2.flags |= 8192), newProps ? 0 !== (renderLanes2 & 536870912) && 0 === (workInProgress2.flags & 128) && (bubbleProperties(workInProgress2), workInProgress2.subtreeFlags & 6 && (workInProgress2.flags |= 8192)) : bubbleProperties(workInProgress2), renderLanes2 = workInProgress2.updateQueue, null !== renderLanes2 && scheduleRetryEffect(workInProgress2, renderLanes2.retryQueue), renderLanes2 = null, null !== current && null !== current.memoizedState && null !== current.memoizedState.cachePool && (renderLanes2 = current.memoizedState.cachePool.pool), newProps = null, null !== workInProgress2.memoizedState && null !== workInProgress2.memoizedState.cachePool && (newProps = workInProgress2.memoizedState.cachePool.pool), newProps !== renderLanes2 && (workInProgress2.flags |= 2048), null !== current && pop(resumedCache), null;
          case 24:
            return renderLanes2 = null, null !== current && (renderLanes2 = current.memoizedState.cache), workInProgress2.memoizedState.cache !== renderLanes2 && (workInProgress2.flags |= 2048), popProvider(CacheContext), bubbleProperties(workInProgress2), null;
          case 25:
            return null;
          case 30:
            return null;
        }
        throw Error(formatProdErrorMessage(156, workInProgress2.tag));
      }
      function unwindWork(current, workInProgress2) {
        popTreeContext(workInProgress2);
        switch (workInProgress2.tag) {
          case 1:
            return current = workInProgress2.flags, current & 65536 ? (workInProgress2.flags = current & -65537 | 128, workInProgress2) : null;
          case 3:
            return popProvider(CacheContext), popHostContainer(), current = workInProgress2.flags, 0 !== (current & 65536) && 0 === (current & 128) ? (workInProgress2.flags = current & -65537 | 128, workInProgress2) : null;
          case 26:
          case 27:
          case 5:
            return popHostContext(workInProgress2), null;
          case 31:
            if (null !== workInProgress2.memoizedState) {
              popSuspenseHandler(workInProgress2);
              if (null === workInProgress2.alternate)
                throw Error(formatProdErrorMessage(340));
              resetHydrationState();
            }
            current = workInProgress2.flags;
            return current & 65536 ? (workInProgress2.flags = current & -65537 | 128, workInProgress2) : null;
          case 13:
            popSuspenseHandler(workInProgress2);
            current = workInProgress2.memoizedState;
            if (null !== current && null !== current.dehydrated) {
              if (null === workInProgress2.alternate)
                throw Error(formatProdErrorMessage(340));
              resetHydrationState();
            }
            current = workInProgress2.flags;
            return current & 65536 ? (workInProgress2.flags = current & -65537 | 128, workInProgress2) : null;
          case 19:
            return pop(suspenseStackCursor), null;
          case 4:
            return popHostContainer(), null;
          case 10:
            return popProvider(workInProgress2.type), null;
          case 22:
          case 23:
            return popSuspenseHandler(workInProgress2), popHiddenContext(), null !== current && pop(resumedCache), current = workInProgress2.flags, current & 65536 ? (workInProgress2.flags = current & -65537 | 128, workInProgress2) : null;
          case 24:
            return popProvider(CacheContext), null;
          case 25:
            return null;
          default:
            return null;
        }
      }
      function unwindInterruptedWork(current, interruptedWork) {
        popTreeContext(interruptedWork);
        switch (interruptedWork.tag) {
          case 3:
            popProvider(CacheContext);
            popHostContainer();
            break;
          case 26:
          case 27:
          case 5:
            popHostContext(interruptedWork);
            break;
          case 4:
            popHostContainer();
            break;
          case 31:
            null !== interruptedWork.memoizedState && popSuspenseHandler(interruptedWork);
            break;
          case 13:
            popSuspenseHandler(interruptedWork);
            break;
          case 19:
            pop(suspenseStackCursor);
            break;
          case 10:
            popProvider(interruptedWork.type);
            break;
          case 22:
          case 23:
            popSuspenseHandler(interruptedWork);
            popHiddenContext();
            null !== current && pop(resumedCache);
            break;
          case 24:
            popProvider(CacheContext);
        }
      }
      function commitHookEffectListMount(flags, finishedWork) {
        try {
          var updateQueue = finishedWork.updateQueue, lastEffect = null !== updateQueue ? updateQueue.lastEffect : null;
          if (null !== lastEffect) {
            var firstEffect = lastEffect.next;
            updateQueue = firstEffect;
            do {
              if ((updateQueue.tag & flags) === flags) {
                lastEffect = void 0;
                var create = updateQueue.create, inst = updateQueue.inst;
                lastEffect = create();
                inst.destroy = lastEffect;
              }
              updateQueue = updateQueue.next;
            } while (updateQueue !== firstEffect);
          }
        } catch (error) {
          captureCommitPhaseError(finishedWork, finishedWork.return, error);
        }
      }
      function commitHookEffectListUnmount(flags, finishedWork, nearestMountedAncestor$jscomp$0) {
        try {
          var updateQueue = finishedWork.updateQueue, lastEffect = null !== updateQueue ? updateQueue.lastEffect : null;
          if (null !== lastEffect) {
            var firstEffect = lastEffect.next;
            updateQueue = firstEffect;
            do {
              if ((updateQueue.tag & flags) === flags) {
                var inst = updateQueue.inst, destroy = inst.destroy;
                if (void 0 !== destroy) {
                  inst.destroy = void 0;
                  lastEffect = finishedWork;
                  var nearestMountedAncestor = nearestMountedAncestor$jscomp$0, destroy_ = destroy;
                  try {
                    destroy_();
                  } catch (error) {
                    captureCommitPhaseError(
                      lastEffect,
                      nearestMountedAncestor,
                      error
                    );
                  }
                }
              }
              updateQueue = updateQueue.next;
            } while (updateQueue !== firstEffect);
          }
        } catch (error) {
          captureCommitPhaseError(finishedWork, finishedWork.return, error);
        }
      }
      function commitClassCallbacks(finishedWork) {
        var updateQueue = finishedWork.updateQueue;
        if (null !== updateQueue) {
          var instance = finishedWork.stateNode;
          try {
            commitCallbacks(updateQueue, instance);
          } catch (error) {
            captureCommitPhaseError(finishedWork, finishedWork.return, error);
          }
        }
      }
      function safelyCallComponentWillUnmount(current, nearestMountedAncestor, instance) {
        instance.props = resolveClassComponentProps(
          current.type,
          current.memoizedProps
        );
        instance.state = current.memoizedState;
        try {
          instance.componentWillUnmount();
        } catch (error) {
          captureCommitPhaseError(current, nearestMountedAncestor, error);
        }
      }
      function safelyAttachRef(current, nearestMountedAncestor) {
        try {
          var ref = current.ref;
          if (null !== ref) {
            switch (current.tag) {
              case 26:
              case 27:
              case 5:
                var instanceToUse = current.stateNode;
                break;
              case 30:
                instanceToUse = current.stateNode;
                break;
              default:
                instanceToUse = current.stateNode;
            }
            "function" === typeof ref ? current.refCleanup = ref(instanceToUse) : ref.current = instanceToUse;
          }
        } catch (error) {
          captureCommitPhaseError(current, nearestMountedAncestor, error);
        }
      }
      function safelyDetachRef(current, nearestMountedAncestor) {
        var ref = current.ref, refCleanup = current.refCleanup;
        if (null !== ref)
          if ("function" === typeof refCleanup)
            try {
              refCleanup();
            } catch (error) {
              captureCommitPhaseError(current, nearestMountedAncestor, error);
            } finally {
              current.refCleanup = null, current = current.alternate, null != current && (current.refCleanup = null);
            }
          else if ("function" === typeof ref)
            try {
              ref(null);
            } catch (error$140) {
              captureCommitPhaseError(current, nearestMountedAncestor, error$140);
            }
          else ref.current = null;
      }
      function commitHostMount(finishedWork) {
        var type = finishedWork.type, props = finishedWork.memoizedProps, instance = finishedWork.stateNode;
        try {
          a: switch (type) {
            case "button":
            case "input":
            case "select":
            case "textarea":
              props.autoFocus && instance.focus();
              break a;
            case "img":
              props.src ? instance.src = props.src : props.srcSet && (instance.srcset = props.srcSet);
          }
        } catch (error) {
          captureCommitPhaseError(finishedWork, finishedWork.return, error);
        }
      }
      function commitHostUpdate(finishedWork, newProps, oldProps) {
        try {
          var domElement = finishedWork.stateNode;
          updateProperties(domElement, finishedWork.type, oldProps, newProps);
          domElement[internalPropsKey] = newProps;
        } catch (error) {
          captureCommitPhaseError(finishedWork, finishedWork.return, error);
        }
      }
      function isHostParent(fiber) {
        return 5 === fiber.tag || 3 === fiber.tag || 26 === fiber.tag || 27 === fiber.tag && isSingletonScope(fiber.type) || 4 === fiber.tag;
      }
      function getHostSibling(fiber) {
        a: for (; ; ) {
          for (; null === fiber.sibling; ) {
            if (null === fiber.return || isHostParent(fiber.return)) return null;
            fiber = fiber.return;
          }
          fiber.sibling.return = fiber.return;
          for (fiber = fiber.sibling; 5 !== fiber.tag && 6 !== fiber.tag && 18 !== fiber.tag; ) {
            if (27 === fiber.tag && isSingletonScope(fiber.type)) continue a;
            if (fiber.flags & 2) continue a;
            if (null === fiber.child || 4 === fiber.tag) continue a;
            else fiber.child.return = fiber, fiber = fiber.child;
          }
          if (!(fiber.flags & 2)) return fiber.stateNode;
        }
      }
      function insertOrAppendPlacementNodeIntoContainer(node, before, parent) {
        var tag = node.tag;
        if (5 === tag || 6 === tag)
          node = node.stateNode, before ? (9 === parent.nodeType ? parent.body : "HTML" === parent.nodeName ? parent.ownerDocument.body : parent).insertBefore(node, before) : (before = 9 === parent.nodeType ? parent.body : "HTML" === parent.nodeName ? parent.ownerDocument.body : parent, before.appendChild(node), parent = parent._reactRootContainer, null !== parent && void 0 !== parent || null !== before.onclick || (before.onclick = noop$1));
        else if (4 !== tag && (27 === tag && isSingletonScope(node.type) && (parent = node.stateNode, before = null), node = node.child, null !== node))
          for (insertOrAppendPlacementNodeIntoContainer(node, before, parent), node = node.sibling; null !== node; )
            insertOrAppendPlacementNodeIntoContainer(node, before, parent), node = node.sibling;
      }
      function insertOrAppendPlacementNode(node, before, parent) {
        var tag = node.tag;
        if (5 === tag || 6 === tag)
          node = node.stateNode, before ? parent.insertBefore(node, before) : parent.appendChild(node);
        else if (4 !== tag && (27 === tag && isSingletonScope(node.type) && (parent = node.stateNode), node = node.child, null !== node))
          for (insertOrAppendPlacementNode(node, before, parent), node = node.sibling; null !== node; )
            insertOrAppendPlacementNode(node, before, parent), node = node.sibling;
      }
      function commitHostSingletonAcquisition(finishedWork) {
        var singleton = finishedWork.stateNode, props = finishedWork.memoizedProps;
        try {
          for (var type = finishedWork.type, attributes = singleton.attributes; attributes.length; )
            singleton.removeAttributeNode(attributes[0]);
          setInitialProperties(singleton, type, props);
          singleton[internalInstanceKey] = finishedWork;
          singleton[internalPropsKey] = props;
        } catch (error) {
          captureCommitPhaseError(finishedWork, finishedWork.return, error);
        }
      }
      var offscreenSubtreeIsHidden = false;
      var offscreenSubtreeWasHidden = false;
      var needsFormReset = false;
      var PossiblyWeakSet = "function" === typeof WeakSet ? WeakSet : Set;
      var nextEffect = null;
      function commitBeforeMutationEffects(root2, firstChild) {
        root2 = root2.containerInfo;
        eventsEnabled = _enabled;
        root2 = getActiveElementDeep(root2);
        if (hasSelectionCapabilities(root2)) {
          if ("selectionStart" in root2)
            var JSCompiler_temp = {
              start: root2.selectionStart,
              end: root2.selectionEnd
            };
          else
            a: {
              JSCompiler_temp = (JSCompiler_temp = root2.ownerDocument) && JSCompiler_temp.defaultView || window;
              var selection = JSCompiler_temp.getSelection && JSCompiler_temp.getSelection();
              if (selection && 0 !== selection.rangeCount) {
                JSCompiler_temp = selection.anchorNode;
                var anchorOffset = selection.anchorOffset, focusNode = selection.focusNode;
                selection = selection.focusOffset;
                try {
                  JSCompiler_temp.nodeType, focusNode.nodeType;
                } catch (e$20) {
                  JSCompiler_temp = null;
                  break a;
                }
                var length = 0, start = -1, end = -1, indexWithinAnchor = 0, indexWithinFocus = 0, node = root2, parentNode = null;
                b: for (; ; ) {
                  for (var next; ; ) {
                    node !== JSCompiler_temp || 0 !== anchorOffset && 3 !== node.nodeType || (start = length + anchorOffset);
                    node !== focusNode || 0 !== selection && 3 !== node.nodeType || (end = length + selection);
                    3 === node.nodeType && (length += node.nodeValue.length);
                    if (null === (next = node.firstChild)) break;
                    parentNode = node;
                    node = next;
                  }
                  for (; ; ) {
                    if (node === root2) break b;
                    parentNode === JSCompiler_temp && ++indexWithinAnchor === anchorOffset && (start = length);
                    parentNode === focusNode && ++indexWithinFocus === selection && (end = length);
                    if (null !== (next = node.nextSibling)) break;
                    node = parentNode;
                    parentNode = node.parentNode;
                  }
                  node = next;
                }
                JSCompiler_temp = -1 === start || -1 === end ? null : { start, end };
              } else JSCompiler_temp = null;
            }
          JSCompiler_temp = JSCompiler_temp || { start: 0, end: 0 };
        } else JSCompiler_temp = null;
        selectionInformation = { focusedElem: root2, selectionRange: JSCompiler_temp };
        _enabled = false;
        for (nextEffect = firstChild; null !== nextEffect; )
          if (firstChild = nextEffect, root2 = firstChild.child, 0 !== (firstChild.subtreeFlags & 1028) && null !== root2)
            root2.return = firstChild, nextEffect = root2;
          else
            for (; null !== nextEffect; ) {
              firstChild = nextEffect;
              focusNode = firstChild.alternate;
              root2 = firstChild.flags;
              switch (firstChild.tag) {
                case 0:
                  if (0 !== (root2 & 4) && (root2 = firstChild.updateQueue, root2 = null !== root2 ? root2.events : null, null !== root2))
                    for (JSCompiler_temp = 0; JSCompiler_temp < root2.length; JSCompiler_temp++)
                      anchorOffset = root2[JSCompiler_temp], anchorOffset.ref.impl = anchorOffset.nextImpl;
                  break;
                case 11:
                case 15:
                  break;
                case 1:
                  if (0 !== (root2 & 1024) && null !== focusNode) {
                    root2 = void 0;
                    JSCompiler_temp = firstChild;
                    anchorOffset = focusNode.memoizedProps;
                    focusNode = focusNode.memoizedState;
                    selection = JSCompiler_temp.stateNode;
                    try {
                      var resolvedPrevProps = resolveClassComponentProps(
                        JSCompiler_temp.type,
                        anchorOffset
                      );
                      root2 = selection.getSnapshotBeforeUpdate(
                        resolvedPrevProps,
                        focusNode
                      );
                      selection.__reactInternalSnapshotBeforeUpdate = root2;
                    } catch (error) {
                      captureCommitPhaseError(
                        JSCompiler_temp,
                        JSCompiler_temp.return,
                        error
                      );
                    }
                  }
                  break;
                case 3:
                  if (0 !== (root2 & 1024)) {
                    if (root2 = firstChild.stateNode.containerInfo, JSCompiler_temp = root2.nodeType, 9 === JSCompiler_temp)
                      clearContainerSparingly(root2);
                    else if (1 === JSCompiler_temp)
                      switch (root2.nodeName) {
                        case "HEAD":
                        case "HTML":
                        case "BODY":
                          clearContainerSparingly(root2);
                          break;
                        default:
                          root2.textContent = "";
                      }
                  }
                  break;
                case 5:
                case 26:
                case 27:
                case 6:
                case 4:
                case 17:
                  break;
                default:
                  if (0 !== (root2 & 1024)) throw Error(formatProdErrorMessage(163));
              }
              root2 = firstChild.sibling;
              if (null !== root2) {
                root2.return = firstChild.return;
                nextEffect = root2;
                break;
              }
              nextEffect = firstChild.return;
            }
      }
      function commitLayoutEffectOnFiber(finishedRoot, current, finishedWork) {
        var flags = finishedWork.flags;
        switch (finishedWork.tag) {
          case 0:
          case 11:
          case 15:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            flags & 4 && commitHookEffectListMount(5, finishedWork);
            break;
          case 1:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            if (flags & 4)
              if (finishedRoot = finishedWork.stateNode, null === current)
                try {
                  finishedRoot.componentDidMount();
                } catch (error) {
                  captureCommitPhaseError(finishedWork, finishedWork.return, error);
                }
              else {
                var prevProps = resolveClassComponentProps(
                  finishedWork.type,
                  current.memoizedProps
                );
                current = current.memoizedState;
                try {
                  finishedRoot.componentDidUpdate(
                    prevProps,
                    current,
                    finishedRoot.__reactInternalSnapshotBeforeUpdate
                  );
                } catch (error$139) {
                  captureCommitPhaseError(
                    finishedWork,
                    finishedWork.return,
                    error$139
                  );
                }
              }
            flags & 64 && commitClassCallbacks(finishedWork);
            flags & 512 && safelyAttachRef(finishedWork, finishedWork.return);
            break;
          case 3:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            if (flags & 64 && (finishedRoot = finishedWork.updateQueue, null !== finishedRoot)) {
              current = null;
              if (null !== finishedWork.child)
                switch (finishedWork.child.tag) {
                  case 27:
                  case 5:
                    current = finishedWork.child.stateNode;
                    break;
                  case 1:
                    current = finishedWork.child.stateNode;
                }
              try {
                commitCallbacks(finishedRoot, current);
              } catch (error) {
                captureCommitPhaseError(finishedWork, finishedWork.return, error);
              }
            }
            break;
          case 27:
            null === current && flags & 4 && commitHostSingletonAcquisition(finishedWork);
          case 26:
          case 5:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            null === current && flags & 4 && commitHostMount(finishedWork);
            flags & 512 && safelyAttachRef(finishedWork, finishedWork.return);
            break;
          case 12:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            break;
          case 31:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            flags & 4 && commitActivityHydrationCallbacks(finishedRoot, finishedWork);
            break;
          case 13:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
            flags & 4 && commitSuspenseHydrationCallbacks(finishedRoot, finishedWork);
            flags & 64 && (finishedRoot = finishedWork.memoizedState, null !== finishedRoot && (finishedRoot = finishedRoot.dehydrated, null !== finishedRoot && (finishedWork = retryDehydratedSuspenseBoundary.bind(
              null,
              finishedWork
            ), registerSuspenseInstanceRetry(finishedRoot, finishedWork))));
            break;
          case 22:
            flags = null !== finishedWork.memoizedState || offscreenSubtreeIsHidden;
            if (!flags) {
              current = null !== current && null !== current.memoizedState || offscreenSubtreeWasHidden;
              prevProps = offscreenSubtreeIsHidden;
              var prevOffscreenSubtreeWasHidden = offscreenSubtreeWasHidden;
              offscreenSubtreeIsHidden = flags;
              (offscreenSubtreeWasHidden = current) && !prevOffscreenSubtreeWasHidden ? recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                0 !== (finishedWork.subtreeFlags & 8772)
              ) : recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
              offscreenSubtreeIsHidden = prevProps;
              offscreenSubtreeWasHidden = prevOffscreenSubtreeWasHidden;
            }
            break;
          case 30:
            break;
          default:
            recursivelyTraverseLayoutEffects(finishedRoot, finishedWork);
        }
      }
      function detachFiberAfterEffects(fiber) {
        var alternate = fiber.alternate;
        null !== alternate && (fiber.alternate = null, detachFiberAfterEffects(alternate));
        fiber.child = null;
        fiber.deletions = null;
        fiber.sibling = null;
        5 === fiber.tag && (alternate = fiber.stateNode, null !== alternate && detachDeletedInstance(alternate));
        fiber.stateNode = null;
        fiber.return = null;
        fiber.dependencies = null;
        fiber.memoizedProps = null;
        fiber.memoizedState = null;
        fiber.pendingProps = null;
        fiber.stateNode = null;
        fiber.updateQueue = null;
      }
      var hostParent = null;
      var hostParentIsContainer = false;
      function recursivelyTraverseDeletionEffects(finishedRoot, nearestMountedAncestor, parent) {
        for (parent = parent.child; null !== parent; )
          commitDeletionEffectsOnFiber(finishedRoot, nearestMountedAncestor, parent), parent = parent.sibling;
      }
      function commitDeletionEffectsOnFiber(finishedRoot, nearestMountedAncestor, deletedFiber) {
        if (injectedHook && "function" === typeof injectedHook.onCommitFiberUnmount)
          try {
            injectedHook.onCommitFiberUnmount(rendererID, deletedFiber);
          } catch (err) {
          }
        switch (deletedFiber.tag) {
          case 26:
            offscreenSubtreeWasHidden || safelyDetachRef(deletedFiber, nearestMountedAncestor);
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            deletedFiber.memoizedState ? deletedFiber.memoizedState.count-- : deletedFiber.stateNode && (deletedFiber = deletedFiber.stateNode, deletedFiber.parentNode.removeChild(deletedFiber));
            break;
          case 27:
            offscreenSubtreeWasHidden || safelyDetachRef(deletedFiber, nearestMountedAncestor);
            var prevHostParent = hostParent, prevHostParentIsContainer = hostParentIsContainer;
            isSingletonScope(deletedFiber.type) && (hostParent = deletedFiber.stateNode, hostParentIsContainer = false);
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            releaseSingletonInstance(deletedFiber.stateNode);
            hostParent = prevHostParent;
            hostParentIsContainer = prevHostParentIsContainer;
            break;
          case 5:
            offscreenSubtreeWasHidden || safelyDetachRef(deletedFiber, nearestMountedAncestor);
          case 6:
            prevHostParent = hostParent;
            prevHostParentIsContainer = hostParentIsContainer;
            hostParent = null;
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            hostParent = prevHostParent;
            hostParentIsContainer = prevHostParentIsContainer;
            if (null !== hostParent)
              if (hostParentIsContainer)
                try {
                  (9 === hostParent.nodeType ? hostParent.body : "HTML" === hostParent.nodeName ? hostParent.ownerDocument.body : hostParent).removeChild(deletedFiber.stateNode);
                } catch (error) {
                  captureCommitPhaseError(
                    deletedFiber,
                    nearestMountedAncestor,
                    error
                  );
                }
              else
                try {
                  hostParent.removeChild(deletedFiber.stateNode);
                } catch (error) {
                  captureCommitPhaseError(
                    deletedFiber,
                    nearestMountedAncestor,
                    error
                  );
                }
            break;
          case 18:
            null !== hostParent && (hostParentIsContainer ? (finishedRoot = hostParent, clearHydrationBoundary(
              9 === finishedRoot.nodeType ? finishedRoot.body : "HTML" === finishedRoot.nodeName ? finishedRoot.ownerDocument.body : finishedRoot,
              deletedFiber.stateNode
            ), retryIfBlockedOn(finishedRoot)) : clearHydrationBoundary(hostParent, deletedFiber.stateNode));
            break;
          case 4:
            prevHostParent = hostParent;
            prevHostParentIsContainer = hostParentIsContainer;
            hostParent = deletedFiber.stateNode.containerInfo;
            hostParentIsContainer = true;
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            hostParent = prevHostParent;
            hostParentIsContainer = prevHostParentIsContainer;
            break;
          case 0:
          case 11:
          case 14:
          case 15:
            commitHookEffectListUnmount(2, deletedFiber, nearestMountedAncestor);
            offscreenSubtreeWasHidden || commitHookEffectListUnmount(4, deletedFiber, nearestMountedAncestor);
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            break;
          case 1:
            offscreenSubtreeWasHidden || (safelyDetachRef(deletedFiber, nearestMountedAncestor), prevHostParent = deletedFiber.stateNode, "function" === typeof prevHostParent.componentWillUnmount && safelyCallComponentWillUnmount(
              deletedFiber,
              nearestMountedAncestor,
              prevHostParent
            ));
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            break;
          case 21:
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            break;
          case 22:
            offscreenSubtreeWasHidden = (prevHostParent = offscreenSubtreeWasHidden) || null !== deletedFiber.memoizedState;
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
            offscreenSubtreeWasHidden = prevHostParent;
            break;
          default:
            recursivelyTraverseDeletionEffects(
              finishedRoot,
              nearestMountedAncestor,
              deletedFiber
            );
        }
      }
      function commitActivityHydrationCallbacks(finishedRoot, finishedWork) {
        if (null === finishedWork.memoizedState && (finishedRoot = finishedWork.alternate, null !== finishedRoot && (finishedRoot = finishedRoot.memoizedState, null !== finishedRoot))) {
          finishedRoot = finishedRoot.dehydrated;
          try {
            retryIfBlockedOn(finishedRoot);
          } catch (error) {
            captureCommitPhaseError(finishedWork, finishedWork.return, error);
          }
        }
      }
      function commitSuspenseHydrationCallbacks(finishedRoot, finishedWork) {
        if (null === finishedWork.memoizedState && (finishedRoot = finishedWork.alternate, null !== finishedRoot && (finishedRoot = finishedRoot.memoizedState, null !== finishedRoot && (finishedRoot = finishedRoot.dehydrated, null !== finishedRoot))))
          try {
            retryIfBlockedOn(finishedRoot);
          } catch (error) {
            captureCommitPhaseError(finishedWork, finishedWork.return, error);
          }
      }
      function getRetryCache(finishedWork) {
        switch (finishedWork.tag) {
          case 31:
          case 13:
          case 19:
            var retryCache = finishedWork.stateNode;
            null === retryCache && (retryCache = finishedWork.stateNode = new PossiblyWeakSet());
            return retryCache;
          case 22:
            return finishedWork = finishedWork.stateNode, retryCache = finishedWork._retryCache, null === retryCache && (retryCache = finishedWork._retryCache = new PossiblyWeakSet()), retryCache;
          default:
            throw Error(formatProdErrorMessage(435, finishedWork.tag));
        }
      }
      function attachSuspenseRetryListeners(finishedWork, wakeables) {
        var retryCache = getRetryCache(finishedWork);
        wakeables.forEach(function(wakeable) {
          if (!retryCache.has(wakeable)) {
            retryCache.add(wakeable);
            var retry = resolveRetryWakeable.bind(null, finishedWork, wakeable);
            wakeable.then(retry, retry);
          }
        });
      }
      function recursivelyTraverseMutationEffects(root$jscomp$0, parentFiber) {
        var deletions = parentFiber.deletions;
        if (null !== deletions)
          for (var i = 0; i < deletions.length; i++) {
            var childToDelete = deletions[i], root2 = root$jscomp$0, returnFiber = parentFiber, parent = returnFiber;
            a: for (; null !== parent; ) {
              switch (parent.tag) {
                case 27:
                  if (isSingletonScope(parent.type)) {
                    hostParent = parent.stateNode;
                    hostParentIsContainer = false;
                    break a;
                  }
                  break;
                case 5:
                  hostParent = parent.stateNode;
                  hostParentIsContainer = false;
                  break a;
                case 3:
                case 4:
                  hostParent = parent.stateNode.containerInfo;
                  hostParentIsContainer = true;
                  break a;
              }
              parent = parent.return;
            }
            if (null === hostParent) throw Error(formatProdErrorMessage(160));
            commitDeletionEffectsOnFiber(root2, returnFiber, childToDelete);
            hostParent = null;
            hostParentIsContainer = false;
            root2 = childToDelete.alternate;
            null !== root2 && (root2.return = null);
            childToDelete.return = null;
          }
        if (parentFiber.subtreeFlags & 13886)
          for (parentFiber = parentFiber.child; null !== parentFiber; )
            commitMutationEffectsOnFiber(parentFiber, root$jscomp$0), parentFiber = parentFiber.sibling;
      }
      var currentHoistableRoot = null;
      function commitMutationEffectsOnFiber(finishedWork, root2) {
        var current = finishedWork.alternate, flags = finishedWork.flags;
        switch (finishedWork.tag) {
          case 0:
          case 11:
          case 14:
          case 15:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 4 && (commitHookEffectListUnmount(3, finishedWork, finishedWork.return), commitHookEffectListMount(3, finishedWork), commitHookEffectListUnmount(5, finishedWork, finishedWork.return));
            break;
          case 1:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 512 && (offscreenSubtreeWasHidden || null === current || safelyDetachRef(current, current.return));
            flags & 64 && offscreenSubtreeIsHidden && (finishedWork = finishedWork.updateQueue, null !== finishedWork && (flags = finishedWork.callbacks, null !== flags && (current = finishedWork.shared.hiddenCallbacks, finishedWork.shared.hiddenCallbacks = null === current ? flags : current.concat(flags))));
            break;
          case 26:
            var hoistableRoot = currentHoistableRoot;
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 512 && (offscreenSubtreeWasHidden || null === current || safelyDetachRef(current, current.return));
            if (flags & 4) {
              var currentResource = null !== current ? current.memoizedState : null;
              flags = finishedWork.memoizedState;
              if (null === current)
                if (null === flags)
                  if (null === finishedWork.stateNode) {
                    a: {
                      flags = finishedWork.type;
                      current = finishedWork.memoizedProps;
                      hoistableRoot = hoistableRoot.ownerDocument || hoistableRoot;
                      b: switch (flags) {
                        case "title":
                          currentResource = hoistableRoot.getElementsByTagName("title")[0];
                          if (!currentResource || currentResource[internalHoistableMarker] || currentResource[internalInstanceKey] || "http://www.w3.org/2000/svg" === currentResource.namespaceURI || currentResource.hasAttribute("itemprop"))
                            currentResource = hoistableRoot.createElement(flags), hoistableRoot.head.insertBefore(
                              currentResource,
                              hoistableRoot.querySelector("head > title")
                            );
                          setInitialProperties(currentResource, flags, current);
                          currentResource[internalInstanceKey] = finishedWork;
                          markNodeAsHoistable(currentResource);
                          flags = currentResource;
                          break a;
                        case "link":
                          var maybeNodes = getHydratableHoistableCache(
                            "link",
                            "href",
                            hoistableRoot
                          ).get(flags + (current.href || ""));
                          if (maybeNodes) {
                            for (var i = 0; i < maybeNodes.length; i++)
                              if (currentResource = maybeNodes[i], currentResource.getAttribute("href") === (null == current.href || "" === current.href ? null : current.href) && currentResource.getAttribute("rel") === (null == current.rel ? null : current.rel) && currentResource.getAttribute("title") === (null == current.title ? null : current.title) && currentResource.getAttribute("crossorigin") === (null == current.crossOrigin ? null : current.crossOrigin)) {
                                maybeNodes.splice(i, 1);
                                break b;
                              }
                          }
                          currentResource = hoistableRoot.createElement(flags);
                          setInitialProperties(currentResource, flags, current);
                          hoistableRoot.head.appendChild(currentResource);
                          break;
                        case "meta":
                          if (maybeNodes = getHydratableHoistableCache(
                            "meta",
                            "content",
                            hoistableRoot
                          ).get(flags + (current.content || ""))) {
                            for (i = 0; i < maybeNodes.length; i++)
                              if (currentResource = maybeNodes[i], currentResource.getAttribute("content") === (null == current.content ? null : "" + current.content) && currentResource.getAttribute("name") === (null == current.name ? null : current.name) && currentResource.getAttribute("property") === (null == current.property ? null : current.property) && currentResource.getAttribute("http-equiv") === (null == current.httpEquiv ? null : current.httpEquiv) && currentResource.getAttribute("charset") === (null == current.charSet ? null : current.charSet)) {
                                maybeNodes.splice(i, 1);
                                break b;
                              }
                          }
                          currentResource = hoistableRoot.createElement(flags);
                          setInitialProperties(currentResource, flags, current);
                          hoistableRoot.head.appendChild(currentResource);
                          break;
                        default:
                          throw Error(formatProdErrorMessage(468, flags));
                      }
                      currentResource[internalInstanceKey] = finishedWork;
                      markNodeAsHoistable(currentResource);
                      flags = currentResource;
                    }
                    finishedWork.stateNode = flags;
                  } else
                    mountHoistable(
                      hoistableRoot,
                      finishedWork.type,
                      finishedWork.stateNode
                    );
                else
                  finishedWork.stateNode = acquireResource(
                    hoistableRoot,
                    flags,
                    finishedWork.memoizedProps
                  );
              else
                currentResource !== flags ? (null === currentResource ? null !== current.stateNode && (current = current.stateNode, current.parentNode.removeChild(current)) : currentResource.count--, null === flags ? mountHoistable(
                  hoistableRoot,
                  finishedWork.type,
                  finishedWork.stateNode
                ) : acquireResource(
                  hoistableRoot,
                  flags,
                  finishedWork.memoizedProps
                )) : null === flags && null !== finishedWork.stateNode && commitHostUpdate(
                  finishedWork,
                  finishedWork.memoizedProps,
                  current.memoizedProps
                );
            }
            break;
          case 27:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 512 && (offscreenSubtreeWasHidden || null === current || safelyDetachRef(current, current.return));
            null !== current && flags & 4 && commitHostUpdate(
              finishedWork,
              finishedWork.memoizedProps,
              current.memoizedProps
            );
            break;
          case 5:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 512 && (offscreenSubtreeWasHidden || null === current || safelyDetachRef(current, current.return));
            if (finishedWork.flags & 32) {
              hoistableRoot = finishedWork.stateNode;
              try {
                setTextContent(hoistableRoot, "");
              } catch (error) {
                captureCommitPhaseError(finishedWork, finishedWork.return, error);
              }
            }
            flags & 4 && null != finishedWork.stateNode && (hoistableRoot = finishedWork.memoizedProps, commitHostUpdate(
              finishedWork,
              hoistableRoot,
              null !== current ? current.memoizedProps : hoistableRoot
            ));
            flags & 1024 && (needsFormReset = true);
            break;
          case 6:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            if (flags & 4) {
              if (null === finishedWork.stateNode)
                throw Error(formatProdErrorMessage(162));
              flags = finishedWork.memoizedProps;
              current = finishedWork.stateNode;
              try {
                current.nodeValue = flags;
              } catch (error) {
                captureCommitPhaseError(finishedWork, finishedWork.return, error);
              }
            }
            break;
          case 3:
            tagCaches = null;
            hoistableRoot = currentHoistableRoot;
            currentHoistableRoot = getHoistableRoot(root2.containerInfo);
            recursivelyTraverseMutationEffects(root2, finishedWork);
            currentHoistableRoot = hoistableRoot;
            commitReconciliationEffects(finishedWork);
            if (flags & 4 && null !== current && current.memoizedState.isDehydrated)
              try {
                retryIfBlockedOn(root2.containerInfo);
              } catch (error) {
                captureCommitPhaseError(finishedWork, finishedWork.return, error);
              }
            needsFormReset && (needsFormReset = false, recursivelyResetForms(finishedWork));
            break;
          case 4:
            flags = currentHoistableRoot;
            currentHoistableRoot = getHoistableRoot(
              finishedWork.stateNode.containerInfo
            );
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            currentHoistableRoot = flags;
            break;
          case 12:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            break;
          case 31:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 4 && (flags = finishedWork.updateQueue, null !== flags && (finishedWork.updateQueue = null, attachSuspenseRetryListeners(finishedWork, flags)));
            break;
          case 13:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            finishedWork.child.flags & 8192 && null !== finishedWork.memoizedState !== (null !== current && null !== current.memoizedState) && (globalMostRecentFallbackTime = now());
            flags & 4 && (flags = finishedWork.updateQueue, null !== flags && (finishedWork.updateQueue = null, attachSuspenseRetryListeners(finishedWork, flags)));
            break;
          case 22:
            hoistableRoot = null !== finishedWork.memoizedState;
            var wasHidden = null !== current && null !== current.memoizedState, prevOffscreenSubtreeIsHidden = offscreenSubtreeIsHidden, prevOffscreenSubtreeWasHidden = offscreenSubtreeWasHidden;
            offscreenSubtreeIsHidden = prevOffscreenSubtreeIsHidden || hoistableRoot;
            offscreenSubtreeWasHidden = prevOffscreenSubtreeWasHidden || wasHidden;
            recursivelyTraverseMutationEffects(root2, finishedWork);
            offscreenSubtreeWasHidden = prevOffscreenSubtreeWasHidden;
            offscreenSubtreeIsHidden = prevOffscreenSubtreeIsHidden;
            commitReconciliationEffects(finishedWork);
            if (flags & 8192)
              a: for (root2 = finishedWork.stateNode, root2._visibility = hoistableRoot ? root2._visibility & -2 : root2._visibility | 1, hoistableRoot && (null === current || wasHidden || offscreenSubtreeIsHidden || offscreenSubtreeWasHidden || recursivelyTraverseDisappearLayoutEffects(finishedWork)), current = null, root2 = finishedWork; ; ) {
                if (5 === root2.tag || 26 === root2.tag) {
                  if (null === current) {
                    wasHidden = current = root2;
                    try {
                      if (currentResource = wasHidden.stateNode, hoistableRoot)
                        maybeNodes = currentResource.style, "function" === typeof maybeNodes.setProperty ? maybeNodes.setProperty("display", "none", "important") : maybeNodes.display = "none";
                      else {
                        i = wasHidden.stateNode;
                        var styleProp = wasHidden.memoizedProps.style, display = void 0 !== styleProp && null !== styleProp && styleProp.hasOwnProperty("display") ? styleProp.display : null;
                        i.style.display = null == display || "boolean" === typeof display ? "" : ("" + display).trim();
                      }
                    } catch (error) {
                      captureCommitPhaseError(wasHidden, wasHidden.return, error);
                    }
                  }
                } else if (6 === root2.tag) {
                  if (null === current) {
                    wasHidden = root2;
                    try {
                      wasHidden.stateNode.nodeValue = hoistableRoot ? "" : wasHidden.memoizedProps;
                    } catch (error) {
                      captureCommitPhaseError(wasHidden, wasHidden.return, error);
                    }
                  }
                } else if (18 === root2.tag) {
                  if (null === current) {
                    wasHidden = root2;
                    try {
                      var instance = wasHidden.stateNode;
                      hoistableRoot ? hideOrUnhideDehydratedBoundary(instance, true) : hideOrUnhideDehydratedBoundary(wasHidden.stateNode, false);
                    } catch (error) {
                      captureCommitPhaseError(wasHidden, wasHidden.return, error);
                    }
                  }
                } else if ((22 !== root2.tag && 23 !== root2.tag || null === root2.memoizedState || root2 === finishedWork) && null !== root2.child) {
                  root2.child.return = root2;
                  root2 = root2.child;
                  continue;
                }
                if (root2 === finishedWork) break a;
                for (; null === root2.sibling; ) {
                  if (null === root2.return || root2.return === finishedWork) break a;
                  current === root2 && (current = null);
                  root2 = root2.return;
                }
                current === root2 && (current = null);
                root2.sibling.return = root2.return;
                root2 = root2.sibling;
              }
            flags & 4 && (flags = finishedWork.updateQueue, null !== flags && (current = flags.retryQueue, null !== current && (flags.retryQueue = null, attachSuspenseRetryListeners(finishedWork, current))));
            break;
          case 19:
            recursivelyTraverseMutationEffects(root2, finishedWork);
            commitReconciliationEffects(finishedWork);
            flags & 4 && (flags = finishedWork.updateQueue, null !== flags && (finishedWork.updateQueue = null, attachSuspenseRetryListeners(finishedWork, flags)));
            break;
          case 30:
            break;
          case 21:
            break;
          default:
            recursivelyTraverseMutationEffects(root2, finishedWork), commitReconciliationEffects(finishedWork);
        }
      }
      function commitReconciliationEffects(finishedWork) {
        var flags = finishedWork.flags;
        if (flags & 2) {
          try {
            for (var hostParentFiber, parentFiber = finishedWork.return; null !== parentFiber; ) {
              if (isHostParent(parentFiber)) {
                hostParentFiber = parentFiber;
                break;
              }
              parentFiber = parentFiber.return;
            }
            if (null == hostParentFiber) throw Error(formatProdErrorMessage(160));
            switch (hostParentFiber.tag) {
              case 27:
                var parent = hostParentFiber.stateNode, before = getHostSibling(finishedWork);
                insertOrAppendPlacementNode(finishedWork, before, parent);
                break;
              case 5:
                var parent$141 = hostParentFiber.stateNode;
                hostParentFiber.flags & 32 && (setTextContent(parent$141, ""), hostParentFiber.flags &= -33);
                var before$142 = getHostSibling(finishedWork);
                insertOrAppendPlacementNode(finishedWork, before$142, parent$141);
                break;
              case 3:
              case 4:
                var parent$143 = hostParentFiber.stateNode.containerInfo, before$144 = getHostSibling(finishedWork);
                insertOrAppendPlacementNodeIntoContainer(
                  finishedWork,
                  before$144,
                  parent$143
                );
                break;
              default:
                throw Error(formatProdErrorMessage(161));
            }
          } catch (error) {
            captureCommitPhaseError(finishedWork, finishedWork.return, error);
          }
          finishedWork.flags &= -3;
        }
        flags & 4096 && (finishedWork.flags &= -4097);
      }
      function recursivelyResetForms(parentFiber) {
        if (parentFiber.subtreeFlags & 1024)
          for (parentFiber = parentFiber.child; null !== parentFiber; ) {
            var fiber = parentFiber;
            recursivelyResetForms(fiber);
            5 === fiber.tag && fiber.flags & 1024 && fiber.stateNode.reset();
            parentFiber = parentFiber.sibling;
          }
      }
      function recursivelyTraverseLayoutEffects(root2, parentFiber) {
        if (parentFiber.subtreeFlags & 8772)
          for (parentFiber = parentFiber.child; null !== parentFiber; )
            commitLayoutEffectOnFiber(root2, parentFiber.alternate, parentFiber), parentFiber = parentFiber.sibling;
      }
      function recursivelyTraverseDisappearLayoutEffects(parentFiber) {
        for (parentFiber = parentFiber.child; null !== parentFiber; ) {
          var finishedWork = parentFiber;
          switch (finishedWork.tag) {
            case 0:
            case 11:
            case 14:
            case 15:
              commitHookEffectListUnmount(4, finishedWork, finishedWork.return);
              recursivelyTraverseDisappearLayoutEffects(finishedWork);
              break;
            case 1:
              safelyDetachRef(finishedWork, finishedWork.return);
              var instance = finishedWork.stateNode;
              "function" === typeof instance.componentWillUnmount && safelyCallComponentWillUnmount(
                finishedWork,
                finishedWork.return,
                instance
              );
              recursivelyTraverseDisappearLayoutEffects(finishedWork);
              break;
            case 27:
              releaseSingletonInstance(finishedWork.stateNode);
            case 26:
            case 5:
              safelyDetachRef(finishedWork, finishedWork.return);
              recursivelyTraverseDisappearLayoutEffects(finishedWork);
              break;
            case 22:
              null === finishedWork.memoizedState && recursivelyTraverseDisappearLayoutEffects(finishedWork);
              break;
            case 30:
              recursivelyTraverseDisappearLayoutEffects(finishedWork);
              break;
            default:
              recursivelyTraverseDisappearLayoutEffects(finishedWork);
          }
          parentFiber = parentFiber.sibling;
        }
      }
      function recursivelyTraverseReappearLayoutEffects(finishedRoot$jscomp$0, parentFiber, includeWorkInProgressEffects) {
        includeWorkInProgressEffects = includeWorkInProgressEffects && 0 !== (parentFiber.subtreeFlags & 8772);
        for (parentFiber = parentFiber.child; null !== parentFiber; ) {
          var current = parentFiber.alternate, finishedRoot = finishedRoot$jscomp$0, finishedWork = parentFiber, flags = finishedWork.flags;
          switch (finishedWork.tag) {
            case 0:
            case 11:
            case 15:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              commitHookEffectListMount(4, finishedWork);
              break;
            case 1:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              current = finishedWork;
              finishedRoot = current.stateNode;
              if ("function" === typeof finishedRoot.componentDidMount)
                try {
                  finishedRoot.componentDidMount();
                } catch (error) {
                  captureCommitPhaseError(current, current.return, error);
                }
              current = finishedWork;
              finishedRoot = current.updateQueue;
              if (null !== finishedRoot) {
                var instance = current.stateNode;
                try {
                  var hiddenCallbacks = finishedRoot.shared.hiddenCallbacks;
                  if (null !== hiddenCallbacks)
                    for (finishedRoot.shared.hiddenCallbacks = null, finishedRoot = 0; finishedRoot < hiddenCallbacks.length; finishedRoot++)
                      callCallback(hiddenCallbacks[finishedRoot], instance);
                } catch (error) {
                  captureCommitPhaseError(current, current.return, error);
                }
              }
              includeWorkInProgressEffects && flags & 64 && commitClassCallbacks(finishedWork);
              safelyAttachRef(finishedWork, finishedWork.return);
              break;
            case 27:
              commitHostSingletonAcquisition(finishedWork);
            case 26:
            case 5:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              includeWorkInProgressEffects && null === current && flags & 4 && commitHostMount(finishedWork);
              safelyAttachRef(finishedWork, finishedWork.return);
              break;
            case 12:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              break;
            case 31:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              includeWorkInProgressEffects && flags & 4 && commitActivityHydrationCallbacks(finishedRoot, finishedWork);
              break;
            case 13:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              includeWorkInProgressEffects && flags & 4 && commitSuspenseHydrationCallbacks(finishedRoot, finishedWork);
              break;
            case 22:
              null === finishedWork.memoizedState && recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
              safelyAttachRef(finishedWork, finishedWork.return);
              break;
            case 30:
              break;
            default:
              recursivelyTraverseReappearLayoutEffects(
                finishedRoot,
                finishedWork,
                includeWorkInProgressEffects
              );
          }
          parentFiber = parentFiber.sibling;
        }
      }
      function commitOffscreenPassiveMountEffects(current, finishedWork) {
        var previousCache = null;
        null !== current && null !== current.memoizedState && null !== current.memoizedState.cachePool && (previousCache = current.memoizedState.cachePool.pool);
        current = null;
        null !== finishedWork.memoizedState && null !== finishedWork.memoizedState.cachePool && (current = finishedWork.memoizedState.cachePool.pool);
        current !== previousCache && (null != current && current.refCount++, null != previousCache && releaseCache(previousCache));
      }
      function commitCachePassiveMountEffect(current, finishedWork) {
        current = null;
        null !== finishedWork.alternate && (current = finishedWork.alternate.memoizedState.cache);
        finishedWork = finishedWork.memoizedState.cache;
        finishedWork !== current && (finishedWork.refCount++, null != current && releaseCache(current));
      }
      function recursivelyTraversePassiveMountEffects(root2, parentFiber, committedLanes, committedTransitions) {
        if (parentFiber.subtreeFlags & 10256)
          for (parentFiber = parentFiber.child; null !== parentFiber; )
            commitPassiveMountOnFiber(
              root2,
              parentFiber,
              committedLanes,
              committedTransitions
            ), parentFiber = parentFiber.sibling;
      }
      function commitPassiveMountOnFiber(finishedRoot, finishedWork, committedLanes, committedTransitions) {
        var flags = finishedWork.flags;
        switch (finishedWork.tag) {
          case 0:
          case 11:
          case 15:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            flags & 2048 && commitHookEffectListMount(9, finishedWork);
            break;
          case 1:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            break;
          case 3:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            flags & 2048 && (finishedRoot = null, null !== finishedWork.alternate && (finishedRoot = finishedWork.alternate.memoizedState.cache), finishedWork = finishedWork.memoizedState.cache, finishedWork !== finishedRoot && (finishedWork.refCount++, null != finishedRoot && releaseCache(finishedRoot)));
            break;
          case 12:
            if (flags & 2048) {
              recursivelyTraversePassiveMountEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions
              );
              finishedRoot = finishedWork.stateNode;
              try {
                var _finishedWork$memoize2 = finishedWork.memoizedProps, id = _finishedWork$memoize2.id, onPostCommit = _finishedWork$memoize2.onPostCommit;
                "function" === typeof onPostCommit && onPostCommit(
                  id,
                  null === finishedWork.alternate ? "mount" : "update",
                  finishedRoot.passiveEffectDuration,
                  -0
                );
              } catch (error) {
                captureCommitPhaseError(finishedWork, finishedWork.return, error);
              }
            } else
              recursivelyTraversePassiveMountEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions
              );
            break;
          case 31:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            break;
          case 13:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            break;
          case 23:
            break;
          case 22:
            _finishedWork$memoize2 = finishedWork.stateNode;
            id = finishedWork.alternate;
            null !== finishedWork.memoizedState ? _finishedWork$memoize2._visibility & 2 ? recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            ) : recursivelyTraverseAtomicPassiveEffects(finishedRoot, finishedWork) : _finishedWork$memoize2._visibility & 2 ? recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            ) : (_finishedWork$memoize2._visibility |= 2, recursivelyTraverseReconnectPassiveEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions,
              0 !== (finishedWork.subtreeFlags & 10256) || false
            ));
            flags & 2048 && commitOffscreenPassiveMountEffects(id, finishedWork);
            break;
          case 24:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
            flags & 2048 && commitCachePassiveMountEffect(finishedWork.alternate, finishedWork);
            break;
          default:
            recursivelyTraversePassiveMountEffects(
              finishedRoot,
              finishedWork,
              committedLanes,
              committedTransitions
            );
        }
      }
      function recursivelyTraverseReconnectPassiveEffects(finishedRoot$jscomp$0, parentFiber, committedLanes$jscomp$0, committedTransitions$jscomp$0, includeWorkInProgressEffects) {
        includeWorkInProgressEffects = includeWorkInProgressEffects && (0 !== (parentFiber.subtreeFlags & 10256) || false);
        for (parentFiber = parentFiber.child; null !== parentFiber; ) {
          var finishedRoot = finishedRoot$jscomp$0, finishedWork = parentFiber, committedLanes = committedLanes$jscomp$0, committedTransitions = committedTransitions$jscomp$0, flags = finishedWork.flags;
          switch (finishedWork.tag) {
            case 0:
            case 11:
            case 15:
              recursivelyTraverseReconnectPassiveEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions,
                includeWorkInProgressEffects
              );
              commitHookEffectListMount(8, finishedWork);
              break;
            case 23:
              break;
            case 22:
              var instance = finishedWork.stateNode;
              null !== finishedWork.memoizedState ? instance._visibility & 2 ? recursivelyTraverseReconnectPassiveEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions,
                includeWorkInProgressEffects
              ) : recursivelyTraverseAtomicPassiveEffects(
                finishedRoot,
                finishedWork
              ) : (instance._visibility |= 2, recursivelyTraverseReconnectPassiveEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions,
                includeWorkInProgressEffects
              ));
              includeWorkInProgressEffects && flags & 2048 && commitOffscreenPassiveMountEffects(
                finishedWork.alternate,
                finishedWork
              );
              break;
            case 24:
              recursivelyTraverseReconnectPassiveEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions,
                includeWorkInProgressEffects
              );
              includeWorkInProgressEffects && flags & 2048 && commitCachePassiveMountEffect(finishedWork.alternate, finishedWork);
              break;
            default:
              recursivelyTraverseReconnectPassiveEffects(
                finishedRoot,
                finishedWork,
                committedLanes,
                committedTransitions,
                includeWorkInProgressEffects
              );
          }
          parentFiber = parentFiber.sibling;
        }
      }
      function recursivelyTraverseAtomicPassiveEffects(finishedRoot$jscomp$0, parentFiber) {
        if (parentFiber.subtreeFlags & 10256)
          for (parentFiber = parentFiber.child; null !== parentFiber; ) {
            var finishedRoot = finishedRoot$jscomp$0, finishedWork = parentFiber, flags = finishedWork.flags;
            switch (finishedWork.tag) {
              case 22:
                recursivelyTraverseAtomicPassiveEffects(finishedRoot, finishedWork);
                flags & 2048 && commitOffscreenPassiveMountEffects(
                  finishedWork.alternate,
                  finishedWork
                );
                break;
              case 24:
                recursivelyTraverseAtomicPassiveEffects(finishedRoot, finishedWork);
                flags & 2048 && commitCachePassiveMountEffect(finishedWork.alternate, finishedWork);
                break;
              default:
                recursivelyTraverseAtomicPassiveEffects(finishedRoot, finishedWork);
            }
            parentFiber = parentFiber.sibling;
          }
      }
      var suspenseyCommitFlag = 8192;
      function recursivelyAccumulateSuspenseyCommit(parentFiber, committedLanes, suspendedState) {
        if (parentFiber.subtreeFlags & suspenseyCommitFlag)
          for (parentFiber = parentFiber.child; null !== parentFiber; )
            accumulateSuspenseyCommitOnFiber(
              parentFiber,
              committedLanes,
              suspendedState
            ), parentFiber = parentFiber.sibling;
      }
      function accumulateSuspenseyCommitOnFiber(fiber, committedLanes, suspendedState) {
        switch (fiber.tag) {
          case 26:
            recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            );
            fiber.flags & suspenseyCommitFlag && null !== fiber.memoizedState && suspendResource(
              suspendedState,
              currentHoistableRoot,
              fiber.memoizedState,
              fiber.memoizedProps
            );
            break;
          case 5:
            recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            );
            break;
          case 3:
          case 4:
            var previousHoistableRoot = currentHoistableRoot;
            currentHoistableRoot = getHoistableRoot(fiber.stateNode.containerInfo);
            recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            );
            currentHoistableRoot = previousHoistableRoot;
            break;
          case 22:
            null === fiber.memoizedState && (previousHoistableRoot = fiber.alternate, null !== previousHoistableRoot && null !== previousHoistableRoot.memoizedState ? (previousHoistableRoot = suspenseyCommitFlag, suspenseyCommitFlag = 16777216, recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            ), suspenseyCommitFlag = previousHoistableRoot) : recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            ));
            break;
          default:
            recursivelyAccumulateSuspenseyCommit(
              fiber,
              committedLanes,
              suspendedState
            );
        }
      }
      function detachAlternateSiblings(parentFiber) {
        var previousFiber = parentFiber.alternate;
        if (null !== previousFiber && (parentFiber = previousFiber.child, null !== parentFiber)) {
          previousFiber.child = null;
          do
            previousFiber = parentFiber.sibling, parentFiber.sibling = null, parentFiber = previousFiber;
          while (null !== parentFiber);
        }
      }
      function recursivelyTraversePassiveUnmountEffects(parentFiber) {
        var deletions = parentFiber.deletions;
        if (0 !== (parentFiber.flags & 16)) {
          if (null !== deletions)
            for (var i = 0; i < deletions.length; i++) {
              var childToDelete = deletions[i];
              nextEffect = childToDelete;
              commitPassiveUnmountEffectsInsideOfDeletedTree_begin(
                childToDelete,
                parentFiber
              );
            }
          detachAlternateSiblings(parentFiber);
        }
        if (parentFiber.subtreeFlags & 10256)
          for (parentFiber = parentFiber.child; null !== parentFiber; )
            commitPassiveUnmountOnFiber(parentFiber), parentFiber = parentFiber.sibling;
      }
      function commitPassiveUnmountOnFiber(finishedWork) {
        switch (finishedWork.tag) {
          case 0:
          case 11:
          case 15:
            recursivelyTraversePassiveUnmountEffects(finishedWork);
            finishedWork.flags & 2048 && commitHookEffectListUnmount(9, finishedWork, finishedWork.return);
            break;
          case 3:
            recursivelyTraversePassiveUnmountEffects(finishedWork);
            break;
          case 12:
            recursivelyTraversePassiveUnmountEffects(finishedWork);
            break;
          case 22:
            var instance = finishedWork.stateNode;
            null !== finishedWork.memoizedState && instance._visibility & 2 && (null === finishedWork.return || 13 !== finishedWork.return.tag) ? (instance._visibility &= -3, recursivelyTraverseDisconnectPassiveEffects(finishedWork)) : recursivelyTraversePassiveUnmountEffects(finishedWork);
            break;
          default:
            recursivelyTraversePassiveUnmountEffects(finishedWork);
        }
      }
      function recursivelyTraverseDisconnectPassiveEffects(parentFiber) {
        var deletions = parentFiber.deletions;
        if (0 !== (parentFiber.flags & 16)) {
          if (null !== deletions)
            for (var i = 0; i < deletions.length; i++) {
              var childToDelete = deletions[i];
              nextEffect = childToDelete;
              commitPassiveUnmountEffectsInsideOfDeletedTree_begin(
                childToDelete,
                parentFiber
              );
            }
          detachAlternateSiblings(parentFiber);
        }
        for (parentFiber = parentFiber.child; null !== parentFiber; ) {
          deletions = parentFiber;
          switch (deletions.tag) {
            case 0:
            case 11:
            case 15:
              commitHookEffectListUnmount(8, deletions, deletions.return);
              recursivelyTraverseDisconnectPassiveEffects(deletions);
              break;
            case 22:
              i = deletions.stateNode;
              i._visibility & 2 && (i._visibility &= -3, recursivelyTraverseDisconnectPassiveEffects(deletions));
              break;
            default:
              recursivelyTraverseDisconnectPassiveEffects(deletions);
          }
          parentFiber = parentFiber.sibling;
        }
      }
      function commitPassiveUnmountEffectsInsideOfDeletedTree_begin(deletedSubtreeRoot, nearestMountedAncestor) {
        for (; null !== nextEffect; ) {
          var fiber = nextEffect;
          switch (fiber.tag) {
            case 0:
            case 11:
            case 15:
              commitHookEffectListUnmount(8, fiber, nearestMountedAncestor);
              break;
            case 23:
            case 22:
              if (null !== fiber.memoizedState && null !== fiber.memoizedState.cachePool) {
                var cache2 = fiber.memoizedState.cachePool.pool;
                null != cache2 && cache2.refCount++;
              }
              break;
            case 24:
              releaseCache(fiber.memoizedState.cache);
          }
          cache2 = fiber.child;
          if (null !== cache2) cache2.return = fiber, nextEffect = cache2;
          else
            a: for (fiber = deletedSubtreeRoot; null !== nextEffect; ) {
              cache2 = nextEffect;
              var sibling = cache2.sibling, returnFiber = cache2.return;
              detachFiberAfterEffects(cache2);
              if (cache2 === fiber) {
                nextEffect = null;
                break a;
              }
              if (null !== sibling) {
                sibling.return = returnFiber;
                nextEffect = sibling;
                break a;
              }
              nextEffect = returnFiber;
            }
        }
      }
      var DefaultAsyncDispatcher = {
        getCacheForType: function(resourceType) {
          var cache2 = readContext(CacheContext), cacheForType = cache2.data.get(resourceType);
          void 0 === cacheForType && (cacheForType = resourceType(), cache2.data.set(resourceType, cacheForType));
          return cacheForType;
        },
        cacheSignal: function() {
          return readContext(CacheContext).controller.signal;
        }
      };
      var PossiblyWeakMap = "function" === typeof WeakMap ? WeakMap : Map;
      var executionContext = 0;
      var workInProgressRoot = null;
      var workInProgress = null;
      var workInProgressRootRenderLanes = 0;
      var workInProgressSuspendedReason = 0;
      var workInProgressThrownValue = null;
      var workInProgressRootDidSkipSuspendedSiblings = false;
      var workInProgressRootIsPrerendering = false;
      var workInProgressRootDidAttachPingListener = false;
      var entangledRenderLanes = 0;
      var workInProgressRootExitStatus = 0;
      var workInProgressRootSkippedLanes = 0;
      var workInProgressRootInterleavedUpdatedLanes = 0;
      var workInProgressRootPingedLanes = 0;
      var workInProgressDeferredLane = 0;
      var workInProgressSuspendedRetryLanes = 0;
      var workInProgressRootConcurrentErrors = null;
      var workInProgressRootRecoverableErrors = null;
      var workInProgressRootDidIncludeRecursiveRenderUpdate = false;
      var globalMostRecentFallbackTime = 0;
      var globalMostRecentTransitionTime = 0;
      var workInProgressRootRenderTargetTime = Infinity;
      var workInProgressTransitions = null;
      var legacyErrorBoundariesThatAlreadyFailed = null;
      var pendingEffectsStatus = 0;
      var pendingEffectsRoot = null;
      var pendingFinishedWork = null;
      var pendingEffectsLanes = 0;
      var pendingEffectsRemainingLanes = 0;
      var pendingPassiveTransitions = null;
      var pendingRecoverableErrors = null;
      var nestedUpdateCount = 0;
      var rootWithNestedUpdates = null;
      function requestUpdateLane() {
        return 0 !== (executionContext & 2) && 0 !== workInProgressRootRenderLanes ? workInProgressRootRenderLanes & -workInProgressRootRenderLanes : null !== ReactSharedInternals.T ? requestTransitionLane() : resolveUpdatePriority();
      }
      function requestDeferredLane() {
        if (0 === workInProgressDeferredLane)
          if (0 === (workInProgressRootRenderLanes & 536870912) || isHydrating) {
            var lane = nextTransitionDeferredLane;
            nextTransitionDeferredLane <<= 1;
            0 === (nextTransitionDeferredLane & 3932160) && (nextTransitionDeferredLane = 262144);
            workInProgressDeferredLane = lane;
          } else workInProgressDeferredLane = 536870912;
        lane = suspenseHandlerStackCursor.current;
        null !== lane && (lane.flags |= 32);
        return workInProgressDeferredLane;
      }
      function scheduleUpdateOnFiber(root2, fiber, lane) {
        if (root2 === workInProgressRoot && (2 === workInProgressSuspendedReason || 9 === workInProgressSuspendedReason) || null !== root2.cancelPendingCommit)
          prepareFreshStack(root2, 0), markRootSuspended(
            root2,
            workInProgressRootRenderLanes,
            workInProgressDeferredLane,
            false
          );
        markRootUpdated$1(root2, lane);
        if (0 === (executionContext & 2) || root2 !== workInProgressRoot)
          root2 === workInProgressRoot && (0 === (executionContext & 2) && (workInProgressRootInterleavedUpdatedLanes |= lane), 4 === workInProgressRootExitStatus && markRootSuspended(
            root2,
            workInProgressRootRenderLanes,
            workInProgressDeferredLane,
            false
          )), ensureRootIsScheduled(root2);
      }
      function performWorkOnRoot(root$jscomp$0, lanes, forceSync) {
        if (0 !== (executionContext & 6)) throw Error(formatProdErrorMessage(327));
        var shouldTimeSlice = !forceSync && 0 === (lanes & 127) && 0 === (lanes & root$jscomp$0.expiredLanes) || checkIfRootIsPrerendering(root$jscomp$0, lanes), exitStatus = shouldTimeSlice ? renderRootConcurrent(root$jscomp$0, lanes) : renderRootSync(root$jscomp$0, lanes, true), renderWasConcurrent = shouldTimeSlice;
        do {
          if (0 === exitStatus) {
            workInProgressRootIsPrerendering && !shouldTimeSlice && markRootSuspended(root$jscomp$0, lanes, 0, false);
            break;
          } else {
            forceSync = root$jscomp$0.current.alternate;
            if (renderWasConcurrent && !isRenderConsistentWithExternalStores(forceSync)) {
              exitStatus = renderRootSync(root$jscomp$0, lanes, false);
              renderWasConcurrent = false;
              continue;
            }
            if (2 === exitStatus) {
              renderWasConcurrent = lanes;
              if (root$jscomp$0.errorRecoveryDisabledLanes & renderWasConcurrent)
                var JSCompiler_inline_result = 0;
              else
                JSCompiler_inline_result = root$jscomp$0.pendingLanes & -536870913, JSCompiler_inline_result = 0 !== JSCompiler_inline_result ? JSCompiler_inline_result : JSCompiler_inline_result & 536870912 ? 536870912 : 0;
              if (0 !== JSCompiler_inline_result) {
                lanes = JSCompiler_inline_result;
                a: {
                  var root2 = root$jscomp$0;
                  exitStatus = workInProgressRootConcurrentErrors;
                  var wasRootDehydrated = root2.current.memoizedState.isDehydrated;
                  wasRootDehydrated && (prepareFreshStack(root2, JSCompiler_inline_result).flags |= 256);
                  JSCompiler_inline_result = renderRootSync(
                    root2,
                    JSCompiler_inline_result,
                    false
                  );
                  if (2 !== JSCompiler_inline_result) {
                    if (workInProgressRootDidAttachPingListener && !wasRootDehydrated) {
                      root2.errorRecoveryDisabledLanes |= renderWasConcurrent;
                      workInProgressRootInterleavedUpdatedLanes |= renderWasConcurrent;
                      exitStatus = 4;
                      break a;
                    }
                    renderWasConcurrent = workInProgressRootRecoverableErrors;
                    workInProgressRootRecoverableErrors = exitStatus;
                    null !== renderWasConcurrent && (null === workInProgressRootRecoverableErrors ? workInProgressRootRecoverableErrors = renderWasConcurrent : workInProgressRootRecoverableErrors.push.apply(
                      workInProgressRootRecoverableErrors,
                      renderWasConcurrent
                    ));
                  }
                  exitStatus = JSCompiler_inline_result;
                }
                renderWasConcurrent = false;
                if (2 !== exitStatus) continue;
              }
            }
            if (1 === exitStatus) {
              prepareFreshStack(root$jscomp$0, 0);
              markRootSuspended(root$jscomp$0, lanes, 0, true);
              break;
            }
            a: {
              shouldTimeSlice = root$jscomp$0;
              renderWasConcurrent = exitStatus;
              switch (renderWasConcurrent) {
                case 0:
                case 1:
                  throw Error(formatProdErrorMessage(345));
                case 4:
                  if ((lanes & 4194048) !== lanes) break;
                case 6:
                  markRootSuspended(
                    shouldTimeSlice,
                    lanes,
                    workInProgressDeferredLane,
                    !workInProgressRootDidSkipSuspendedSiblings
                  );
                  break a;
                case 2:
                  workInProgressRootRecoverableErrors = null;
                  break;
                case 3:
                case 5:
                  break;
                default:
                  throw Error(formatProdErrorMessage(329));
              }
              if ((lanes & 62914560) === lanes && (exitStatus = globalMostRecentFallbackTime + 300 - now(), 10 < exitStatus)) {
                markRootSuspended(
                  shouldTimeSlice,
                  lanes,
                  workInProgressDeferredLane,
                  !workInProgressRootDidSkipSuspendedSiblings
                );
                if (0 !== getNextLanes(shouldTimeSlice, 0, true)) break a;
                pendingEffectsLanes = lanes;
                shouldTimeSlice.timeoutHandle = scheduleTimeout(
                  commitRootWhenReady.bind(
                    null,
                    shouldTimeSlice,
                    forceSync,
                    workInProgressRootRecoverableErrors,
                    workInProgressTransitions,
                    workInProgressRootDidIncludeRecursiveRenderUpdate,
                    lanes,
                    workInProgressDeferredLane,
                    workInProgressRootInterleavedUpdatedLanes,
                    workInProgressSuspendedRetryLanes,
                    workInProgressRootDidSkipSuspendedSiblings,
                    renderWasConcurrent,
                    "Throttled",
                    -0,
                    0
                  ),
                  exitStatus
                );
                break a;
              }
              commitRootWhenReady(
                shouldTimeSlice,
                forceSync,
                workInProgressRootRecoverableErrors,
                workInProgressTransitions,
                workInProgressRootDidIncludeRecursiveRenderUpdate,
                lanes,
                workInProgressDeferredLane,
                workInProgressRootInterleavedUpdatedLanes,
                workInProgressSuspendedRetryLanes,
                workInProgressRootDidSkipSuspendedSiblings,
                renderWasConcurrent,
                null,
                -0,
                0
              );
            }
          }
          break;
        } while (1);
        ensureRootIsScheduled(root$jscomp$0);
      }
      function commitRootWhenReady(root2, finishedWork, recoverableErrors, transitions, didIncludeRenderPhaseUpdate, lanes, spawnedLane, updatedLanes, suspendedRetryLanes, didSkipSuspendedSiblings, exitStatus, suspendedCommitReason, completedRenderStartTime, completedRenderEndTime) {
        root2.timeoutHandle = -1;
        suspendedCommitReason = finishedWork.subtreeFlags;
        if (suspendedCommitReason & 8192 || 16785408 === (suspendedCommitReason & 16785408)) {
          suspendedCommitReason = {
            stylesheets: null,
            count: 0,
            imgCount: 0,
            imgBytes: 0,
            suspenseyImages: [],
            waitingForImages: true,
            waitingForViewTransition: false,
            unsuspend: noop$1
          };
          accumulateSuspenseyCommitOnFiber(
            finishedWork,
            lanes,
            suspendedCommitReason
          );
          var timeoutOffset = (lanes & 62914560) === lanes ? globalMostRecentFallbackTime - now() : (lanes & 4194048) === lanes ? globalMostRecentTransitionTime - now() : 0;
          timeoutOffset = waitForCommitToBeReady(
            suspendedCommitReason,
            timeoutOffset
          );
          if (null !== timeoutOffset) {
            pendingEffectsLanes = lanes;
            root2.cancelPendingCommit = timeoutOffset(
              commitRoot.bind(
                null,
                root2,
                finishedWork,
                lanes,
                recoverableErrors,
                transitions,
                didIncludeRenderPhaseUpdate,
                spawnedLane,
                updatedLanes,
                suspendedRetryLanes,
                exitStatus,
                suspendedCommitReason,
                null,
                completedRenderStartTime,
                completedRenderEndTime
              )
            );
            markRootSuspended(root2, lanes, spawnedLane, !didSkipSuspendedSiblings);
            return;
          }
        }
        commitRoot(
          root2,
          finishedWork,
          lanes,
          recoverableErrors,
          transitions,
          didIncludeRenderPhaseUpdate,
          spawnedLane,
          updatedLanes,
          suspendedRetryLanes
        );
      }
      function isRenderConsistentWithExternalStores(finishedWork) {
        for (var node = finishedWork; ; ) {
          var tag = node.tag;
          if ((0 === tag || 11 === tag || 15 === tag) && node.flags & 16384 && (tag = node.updateQueue, null !== tag && (tag = tag.stores, null !== tag)))
            for (var i = 0; i < tag.length; i++) {
              var check = tag[i], getSnapshot = check.getSnapshot;
              check = check.value;
              try {
                if (!objectIs(getSnapshot(), check)) return false;
              } catch (error) {
                return false;
              }
            }
          tag = node.child;
          if (node.subtreeFlags & 16384 && null !== tag)
            tag.return = node, node = tag;
          else {
            if (node === finishedWork) break;
            for (; null === node.sibling; ) {
              if (null === node.return || node.return === finishedWork) return true;
              node = node.return;
            }
            node.sibling.return = node.return;
            node = node.sibling;
          }
        }
        return true;
      }
      function markRootSuspended(root2, suspendedLanes, spawnedLane, didAttemptEntireTree) {
        suspendedLanes &= ~workInProgressRootPingedLanes;
        suspendedLanes &= ~workInProgressRootInterleavedUpdatedLanes;
        root2.suspendedLanes |= suspendedLanes;
        root2.pingedLanes &= ~suspendedLanes;
        didAttemptEntireTree && (root2.warmLanes |= suspendedLanes);
        didAttemptEntireTree = root2.expirationTimes;
        for (var lanes = suspendedLanes; 0 < lanes; ) {
          var index$6 = 31 - clz32(lanes), lane = 1 << index$6;
          didAttemptEntireTree[index$6] = -1;
          lanes &= ~lane;
        }
        0 !== spawnedLane && markSpawnedDeferredLane(root2, spawnedLane, suspendedLanes);
      }
      function flushSyncWork$1() {
        return 0 === (executionContext & 6) ? (flushSyncWorkAcrossRoots_impl(0, false), false) : true;
      }
      function resetWorkInProgressStack() {
        if (null !== workInProgress) {
          if (0 === workInProgressSuspendedReason)
            var interruptedWork = workInProgress.return;
          else
            interruptedWork = workInProgress, lastContextDependency = currentlyRenderingFiber$1 = null, resetHooksOnUnwind(interruptedWork), thenableState$1 = null, thenableIndexCounter$1 = 0, interruptedWork = workInProgress;
          for (; null !== interruptedWork; )
            unwindInterruptedWork(interruptedWork.alternate, interruptedWork), interruptedWork = interruptedWork.return;
          workInProgress = null;
        }
      }
      function prepareFreshStack(root2, lanes) {
        var timeoutHandle = root2.timeoutHandle;
        -1 !== timeoutHandle && (root2.timeoutHandle = -1, cancelTimeout(timeoutHandle));
        timeoutHandle = root2.cancelPendingCommit;
        null !== timeoutHandle && (root2.cancelPendingCommit = null, timeoutHandle());
        pendingEffectsLanes = 0;
        resetWorkInProgressStack();
        workInProgressRoot = root2;
        workInProgress = timeoutHandle = createWorkInProgress(root2.current, null);
        workInProgressRootRenderLanes = lanes;
        workInProgressSuspendedReason = 0;
        workInProgressThrownValue = null;
        workInProgressRootDidSkipSuspendedSiblings = false;
        workInProgressRootIsPrerendering = checkIfRootIsPrerendering(root2, lanes);
        workInProgressRootDidAttachPingListener = false;
        workInProgressSuspendedRetryLanes = workInProgressDeferredLane = workInProgressRootPingedLanes = workInProgressRootInterleavedUpdatedLanes = workInProgressRootSkippedLanes = workInProgressRootExitStatus = 0;
        workInProgressRootRecoverableErrors = workInProgressRootConcurrentErrors = null;
        workInProgressRootDidIncludeRecursiveRenderUpdate = false;
        0 !== (lanes & 8) && (lanes |= lanes & 32);
        var allEntangledLanes = root2.entangledLanes;
        if (0 !== allEntangledLanes)
          for (root2 = root2.entanglements, allEntangledLanes &= lanes; 0 < allEntangledLanes; ) {
            var index$4 = 31 - clz32(allEntangledLanes), lane = 1 << index$4;
            lanes |= root2[index$4];
            allEntangledLanes &= ~lane;
          }
        entangledRenderLanes = lanes;
        finishQueueingConcurrentUpdates();
        return timeoutHandle;
      }
      function handleThrow(root2, thrownValue) {
        currentlyRenderingFiber = null;
        ReactSharedInternals.H = ContextOnlyDispatcher;
        thrownValue === SuspenseException || thrownValue === SuspenseActionException ? (thrownValue = getSuspendedThenable(), workInProgressSuspendedReason = 3) : thrownValue === SuspenseyCommitException ? (thrownValue = getSuspendedThenable(), workInProgressSuspendedReason = 4) : workInProgressSuspendedReason = thrownValue === SelectiveHydrationException ? 8 : null !== thrownValue && "object" === typeof thrownValue && "function" === typeof thrownValue.then ? 6 : 1;
        workInProgressThrownValue = thrownValue;
        null === workInProgress && (workInProgressRootExitStatus = 1, logUncaughtError(
          root2,
          createCapturedValueAtFiber(thrownValue, root2.current)
        ));
      }
      function shouldRemainOnPreviousScreen() {
        var handler = suspenseHandlerStackCursor.current;
        return null === handler ? true : (workInProgressRootRenderLanes & 4194048) === workInProgressRootRenderLanes ? null === shellBoundary ? true : false : (workInProgressRootRenderLanes & 62914560) === workInProgressRootRenderLanes || 0 !== (workInProgressRootRenderLanes & 536870912) ? handler === shellBoundary : false;
      }
      function pushDispatcher() {
        var prevDispatcher = ReactSharedInternals.H;
        ReactSharedInternals.H = ContextOnlyDispatcher;
        return null === prevDispatcher ? ContextOnlyDispatcher : prevDispatcher;
      }
      function pushAsyncDispatcher() {
        var prevAsyncDispatcher = ReactSharedInternals.A;
        ReactSharedInternals.A = DefaultAsyncDispatcher;
        return prevAsyncDispatcher;
      }
      function renderDidSuspendDelayIfPossible() {
        workInProgressRootExitStatus = 4;
        workInProgressRootDidSkipSuspendedSiblings || (workInProgressRootRenderLanes & 4194048) !== workInProgressRootRenderLanes && null !== suspenseHandlerStackCursor.current || (workInProgressRootIsPrerendering = true);
        0 === (workInProgressRootSkippedLanes & 134217727) && 0 === (workInProgressRootInterleavedUpdatedLanes & 134217727) || null === workInProgressRoot || markRootSuspended(
          workInProgressRoot,
          workInProgressRootRenderLanes,
          workInProgressDeferredLane,
          false
        );
      }
      function renderRootSync(root2, lanes, shouldYieldForPrerendering) {
        var prevExecutionContext = executionContext;
        executionContext |= 2;
        var prevDispatcher = pushDispatcher(), prevAsyncDispatcher = pushAsyncDispatcher();
        if (workInProgressRoot !== root2 || workInProgressRootRenderLanes !== lanes)
          workInProgressTransitions = null, prepareFreshStack(root2, lanes);
        lanes = false;
        var exitStatus = workInProgressRootExitStatus;
        a: do
          try {
            if (0 !== workInProgressSuspendedReason && null !== workInProgress) {
              var unitOfWork = workInProgress, thrownValue = workInProgressThrownValue;
              switch (workInProgressSuspendedReason) {
                case 8:
                  resetWorkInProgressStack();
                  exitStatus = 6;
                  break a;
                case 3:
                case 2:
                case 9:
                case 6:
                  null === suspenseHandlerStackCursor.current && (lanes = true);
                  var reason = workInProgressSuspendedReason;
                  workInProgressSuspendedReason = 0;
                  workInProgressThrownValue = null;
                  throwAndUnwindWorkLoop(root2, unitOfWork, thrownValue, reason);
                  if (shouldYieldForPrerendering && workInProgressRootIsPrerendering) {
                    exitStatus = 0;
                    break a;
                  }
                  break;
                default:
                  reason = workInProgressSuspendedReason, workInProgressSuspendedReason = 0, workInProgressThrownValue = null, throwAndUnwindWorkLoop(root2, unitOfWork, thrownValue, reason);
              }
            }
            workLoopSync();
            exitStatus = workInProgressRootExitStatus;
            break;
          } catch (thrownValue$165) {
            handleThrow(root2, thrownValue$165);
          }
        while (1);
        lanes && root2.shellSuspendCounter++;
        lastContextDependency = currentlyRenderingFiber$1 = null;
        executionContext = prevExecutionContext;
        ReactSharedInternals.H = prevDispatcher;
        ReactSharedInternals.A = prevAsyncDispatcher;
        null === workInProgress && (workInProgressRoot = null, workInProgressRootRenderLanes = 0, finishQueueingConcurrentUpdates());
        return exitStatus;
      }
      function workLoopSync() {
        for (; null !== workInProgress; ) performUnitOfWork(workInProgress);
      }
      function renderRootConcurrent(root2, lanes) {
        var prevExecutionContext = executionContext;
        executionContext |= 2;
        var prevDispatcher = pushDispatcher(), prevAsyncDispatcher = pushAsyncDispatcher();
        workInProgressRoot !== root2 || workInProgressRootRenderLanes !== lanes ? (workInProgressTransitions = null, workInProgressRootRenderTargetTime = now() + 500, prepareFreshStack(root2, lanes)) : workInProgressRootIsPrerendering = checkIfRootIsPrerendering(
          root2,
          lanes
        );
        a: do
          try {
            if (0 !== workInProgressSuspendedReason && null !== workInProgress) {
              lanes = workInProgress;
              var thrownValue = workInProgressThrownValue;
              b: switch (workInProgressSuspendedReason) {
                case 1:
                  workInProgressSuspendedReason = 0;
                  workInProgressThrownValue = null;
                  throwAndUnwindWorkLoop(root2, lanes, thrownValue, 1);
                  break;
                case 2:
                case 9:
                  if (isThenableResolved(thrownValue)) {
                    workInProgressSuspendedReason = 0;
                    workInProgressThrownValue = null;
                    replaySuspendedUnitOfWork(lanes);
                    break;
                  }
                  lanes = function() {
                    2 !== workInProgressSuspendedReason && 9 !== workInProgressSuspendedReason || workInProgressRoot !== root2 || (workInProgressSuspendedReason = 7);
                    ensureRootIsScheduled(root2);
                  };
                  thrownValue.then(lanes, lanes);
                  break a;
                case 3:
                  workInProgressSuspendedReason = 7;
                  break a;
                case 4:
                  workInProgressSuspendedReason = 5;
                  break a;
                case 7:
                  isThenableResolved(thrownValue) ? (workInProgressSuspendedReason = 0, workInProgressThrownValue = null, replaySuspendedUnitOfWork(lanes)) : (workInProgressSuspendedReason = 0, workInProgressThrownValue = null, throwAndUnwindWorkLoop(root2, lanes, thrownValue, 7));
                  break;
                case 5:
                  var resource = null;
                  switch (workInProgress.tag) {
                    case 26:
                      resource = workInProgress.memoizedState;
                    case 5:
                    case 27:
                      var hostFiber = workInProgress;
                      if (resource ? preloadResource(resource) : hostFiber.stateNode.complete) {
                        workInProgressSuspendedReason = 0;
                        workInProgressThrownValue = null;
                        var sibling = hostFiber.sibling;
                        if (null !== sibling) workInProgress = sibling;
                        else {
                          var returnFiber = hostFiber.return;
                          null !== returnFiber ? (workInProgress = returnFiber, completeUnitOfWork(returnFiber)) : workInProgress = null;
                        }
                        break b;
                      }
                  }
                  workInProgressSuspendedReason = 0;
                  workInProgressThrownValue = null;
                  throwAndUnwindWorkLoop(root2, lanes, thrownValue, 5);
                  break;
                case 6:
                  workInProgressSuspendedReason = 0;
                  workInProgressThrownValue = null;
                  throwAndUnwindWorkLoop(root2, lanes, thrownValue, 6);
                  break;
                case 8:
                  resetWorkInProgressStack();
                  workInProgressRootExitStatus = 6;
                  break a;
                default:
                  throw Error(formatProdErrorMessage(462));
              }
            }
            workLoopConcurrentByScheduler();
            break;
          } catch (thrownValue$167) {
            handleThrow(root2, thrownValue$167);
          }
        while (1);
        lastContextDependency = currentlyRenderingFiber$1 = null;
        ReactSharedInternals.H = prevDispatcher;
        ReactSharedInternals.A = prevAsyncDispatcher;
        executionContext = prevExecutionContext;
        if (null !== workInProgress) return 0;
        workInProgressRoot = null;
        workInProgressRootRenderLanes = 0;
        finishQueueingConcurrentUpdates();
        return workInProgressRootExitStatus;
      }
      function workLoopConcurrentByScheduler() {
        for (; null !== workInProgress && !shouldYield(); )
          performUnitOfWork(workInProgress);
      }
      function performUnitOfWork(unitOfWork) {
        var next = beginWork(unitOfWork.alternate, unitOfWork, entangledRenderLanes);
        unitOfWork.memoizedProps = unitOfWork.pendingProps;
        null === next ? completeUnitOfWork(unitOfWork) : workInProgress = next;
      }
      function replaySuspendedUnitOfWork(unitOfWork) {
        var next = unitOfWork;
        var current = next.alternate;
        switch (next.tag) {
          case 15:
          case 0:
            next = replayFunctionComponent(
              current,
              next,
              next.pendingProps,
              next.type,
              void 0,
              workInProgressRootRenderLanes
            );
            break;
          case 11:
            next = replayFunctionComponent(
              current,
              next,
              next.pendingProps,
              next.type.render,
              next.ref,
              workInProgressRootRenderLanes
            );
            break;
          case 5:
            resetHooksOnUnwind(next);
          default:
            unwindInterruptedWork(current, next), next = workInProgress = resetWorkInProgress(next, entangledRenderLanes), next = beginWork(current, next, entangledRenderLanes);
        }
        unitOfWork.memoizedProps = unitOfWork.pendingProps;
        null === next ? completeUnitOfWork(unitOfWork) : workInProgress = next;
      }
      function throwAndUnwindWorkLoop(root2, unitOfWork, thrownValue, suspendedReason) {
        lastContextDependency = currentlyRenderingFiber$1 = null;
        resetHooksOnUnwind(unitOfWork);
        thenableState$1 = null;
        thenableIndexCounter$1 = 0;
        var returnFiber = unitOfWork.return;
        try {
          if (throwException(
            root2,
            returnFiber,
            unitOfWork,
            thrownValue,
            workInProgressRootRenderLanes
          )) {
            workInProgressRootExitStatus = 1;
            logUncaughtError(
              root2,
              createCapturedValueAtFiber(thrownValue, root2.current)
            );
            workInProgress = null;
            return;
          }
        } catch (error) {
          if (null !== returnFiber) throw workInProgress = returnFiber, error;
          workInProgressRootExitStatus = 1;
          logUncaughtError(
            root2,
            createCapturedValueAtFiber(thrownValue, root2.current)
          );
          workInProgress = null;
          return;
        }
        if (unitOfWork.flags & 32768) {
          if (isHydrating || 1 === suspendedReason) root2 = true;
          else if (workInProgressRootIsPrerendering || 0 !== (workInProgressRootRenderLanes & 536870912))
            root2 = false;
          else if (workInProgressRootDidSkipSuspendedSiblings = root2 = true, 2 === suspendedReason || 9 === suspendedReason || 3 === suspendedReason || 6 === suspendedReason)
            suspendedReason = suspenseHandlerStackCursor.current, null !== suspendedReason && 13 === suspendedReason.tag && (suspendedReason.flags |= 16384);
          unwindUnitOfWork(unitOfWork, root2);
        } else completeUnitOfWork(unitOfWork);
      }
      function completeUnitOfWork(unitOfWork) {
        var completedWork = unitOfWork;
        do {
          if (0 !== (completedWork.flags & 32768)) {
            unwindUnitOfWork(
              completedWork,
              workInProgressRootDidSkipSuspendedSiblings
            );
            return;
          }
          unitOfWork = completedWork.return;
          var next = completeWork(
            completedWork.alternate,
            completedWork,
            entangledRenderLanes
          );
          if (null !== next) {
            workInProgress = next;
            return;
          }
          completedWork = completedWork.sibling;
          if (null !== completedWork) {
            workInProgress = completedWork;
            return;
          }
          workInProgress = completedWork = unitOfWork;
        } while (null !== completedWork);
        0 === workInProgressRootExitStatus && (workInProgressRootExitStatus = 5);
      }
      function unwindUnitOfWork(unitOfWork, skipSiblings) {
        do {
          var next = unwindWork(unitOfWork.alternate, unitOfWork);
          if (null !== next) {
            next.flags &= 32767;
            workInProgress = next;
            return;
          }
          next = unitOfWork.return;
          null !== next && (next.flags |= 32768, next.subtreeFlags = 0, next.deletions = null);
          if (!skipSiblings && (unitOfWork = unitOfWork.sibling, null !== unitOfWork)) {
            workInProgress = unitOfWork;
            return;
          }
          workInProgress = unitOfWork = next;
        } while (null !== unitOfWork);
        workInProgressRootExitStatus = 6;
        workInProgress = null;
      }
      function commitRoot(root2, finishedWork, lanes, recoverableErrors, transitions, didIncludeRenderPhaseUpdate, spawnedLane, updatedLanes, suspendedRetryLanes) {
        root2.cancelPendingCommit = null;
        do
          flushPendingEffects();
        while (0 !== pendingEffectsStatus);
        if (0 !== (executionContext & 6)) throw Error(formatProdErrorMessage(327));
        if (null !== finishedWork) {
          if (finishedWork === root2.current) throw Error(formatProdErrorMessage(177));
          didIncludeRenderPhaseUpdate = finishedWork.lanes | finishedWork.childLanes;
          didIncludeRenderPhaseUpdate |= concurrentlyUpdatedLanes;
          markRootFinished(
            root2,
            lanes,
            didIncludeRenderPhaseUpdate,
            spawnedLane,
            updatedLanes,
            suspendedRetryLanes
          );
          root2 === workInProgressRoot && (workInProgress = workInProgressRoot = null, workInProgressRootRenderLanes = 0);
          pendingFinishedWork = finishedWork;
          pendingEffectsRoot = root2;
          pendingEffectsLanes = lanes;
          pendingEffectsRemainingLanes = didIncludeRenderPhaseUpdate;
          pendingPassiveTransitions = transitions;
          pendingRecoverableErrors = recoverableErrors;
          0 !== (finishedWork.subtreeFlags & 10256) || 0 !== (finishedWork.flags & 10256) ? (root2.callbackNode = null, root2.callbackPriority = 0, scheduleCallback$1(NormalPriority$1, function() {
            flushPassiveEffects();
            return null;
          })) : (root2.callbackNode = null, root2.callbackPriority = 0);
          recoverableErrors = 0 !== (finishedWork.flags & 13878);
          if (0 !== (finishedWork.subtreeFlags & 13878) || recoverableErrors) {
            recoverableErrors = ReactSharedInternals.T;
            ReactSharedInternals.T = null;
            transitions = ReactDOMSharedInternals.p;
            ReactDOMSharedInternals.p = 2;
            spawnedLane = executionContext;
            executionContext |= 4;
            try {
              commitBeforeMutationEffects(root2, finishedWork, lanes);
            } finally {
              executionContext = spawnedLane, ReactDOMSharedInternals.p = transitions, ReactSharedInternals.T = recoverableErrors;
            }
          }
          pendingEffectsStatus = 1;
          flushMutationEffects();
          flushLayoutEffects();
          flushSpawnedWork();
        }
      }
      function flushMutationEffects() {
        if (1 === pendingEffectsStatus) {
          pendingEffectsStatus = 0;
          var root2 = pendingEffectsRoot, finishedWork = pendingFinishedWork, rootMutationHasEffect = 0 !== (finishedWork.flags & 13878);
          if (0 !== (finishedWork.subtreeFlags & 13878) || rootMutationHasEffect) {
            rootMutationHasEffect = ReactSharedInternals.T;
            ReactSharedInternals.T = null;
            var previousPriority = ReactDOMSharedInternals.p;
            ReactDOMSharedInternals.p = 2;
            var prevExecutionContext = executionContext;
            executionContext |= 4;
            try {
              commitMutationEffectsOnFiber(finishedWork, root2);
              var priorSelectionInformation = selectionInformation, curFocusedElem = getActiveElementDeep(root2.containerInfo), priorFocusedElem = priorSelectionInformation.focusedElem, priorSelectionRange = priorSelectionInformation.selectionRange;
              if (curFocusedElem !== priorFocusedElem && priorFocusedElem && priorFocusedElem.ownerDocument && containsNode(
                priorFocusedElem.ownerDocument.documentElement,
                priorFocusedElem
              )) {
                if (null !== priorSelectionRange && hasSelectionCapabilities(priorFocusedElem)) {
                  var start = priorSelectionRange.start, end = priorSelectionRange.end;
                  void 0 === end && (end = start);
                  if ("selectionStart" in priorFocusedElem)
                    priorFocusedElem.selectionStart = start, priorFocusedElem.selectionEnd = Math.min(
                      end,
                      priorFocusedElem.value.length
                    );
                  else {
                    var doc = priorFocusedElem.ownerDocument || document, win = doc && doc.defaultView || window;
                    if (win.getSelection) {
                      var selection = win.getSelection(), length = priorFocusedElem.textContent.length, start$jscomp$0 = Math.min(priorSelectionRange.start, length), end$jscomp$0 = void 0 === priorSelectionRange.end ? start$jscomp$0 : Math.min(priorSelectionRange.end, length);
                      !selection.extend && start$jscomp$0 > end$jscomp$0 && (curFocusedElem = end$jscomp$0, end$jscomp$0 = start$jscomp$0, start$jscomp$0 = curFocusedElem);
                      var startMarker = getNodeForCharacterOffset(
                        priorFocusedElem,
                        start$jscomp$0
                      ), endMarker = getNodeForCharacterOffset(
                        priorFocusedElem,
                        end$jscomp$0
                      );
                      if (startMarker && endMarker && (1 !== selection.rangeCount || selection.anchorNode !== startMarker.node || selection.anchorOffset !== startMarker.offset || selection.focusNode !== endMarker.node || selection.focusOffset !== endMarker.offset)) {
                        var range = doc.createRange();
                        range.setStart(startMarker.node, startMarker.offset);
                        selection.removeAllRanges();
                        start$jscomp$0 > end$jscomp$0 ? (selection.addRange(range), selection.extend(endMarker.node, endMarker.offset)) : (range.setEnd(endMarker.node, endMarker.offset), selection.addRange(range));
                      }
                    }
                  }
                }
                doc = [];
                for (selection = priorFocusedElem; selection = selection.parentNode; )
                  1 === selection.nodeType && doc.push({
                    element: selection,
                    left: selection.scrollLeft,
                    top: selection.scrollTop
                  });
                "function" === typeof priorFocusedElem.focus && priorFocusedElem.focus();
                for (priorFocusedElem = 0; priorFocusedElem < doc.length; priorFocusedElem++) {
                  var info = doc[priorFocusedElem];
                  info.element.scrollLeft = info.left;
                  info.element.scrollTop = info.top;
                }
              }
              _enabled = !!eventsEnabled;
              selectionInformation = eventsEnabled = null;
            } finally {
              executionContext = prevExecutionContext, ReactDOMSharedInternals.p = previousPriority, ReactSharedInternals.T = rootMutationHasEffect;
            }
          }
          root2.current = finishedWork;
          pendingEffectsStatus = 2;
        }
      }
      function flushLayoutEffects() {
        if (2 === pendingEffectsStatus) {
          pendingEffectsStatus = 0;
          var root2 = pendingEffectsRoot, finishedWork = pendingFinishedWork, rootHasLayoutEffect = 0 !== (finishedWork.flags & 8772);
          if (0 !== (finishedWork.subtreeFlags & 8772) || rootHasLayoutEffect) {
            rootHasLayoutEffect = ReactSharedInternals.T;
            ReactSharedInternals.T = null;
            var previousPriority = ReactDOMSharedInternals.p;
            ReactDOMSharedInternals.p = 2;
            var prevExecutionContext = executionContext;
            executionContext |= 4;
            try {
              commitLayoutEffectOnFiber(root2, finishedWork.alternate, finishedWork);
            } finally {
              executionContext = prevExecutionContext, ReactDOMSharedInternals.p = previousPriority, ReactSharedInternals.T = rootHasLayoutEffect;
            }
          }
          pendingEffectsStatus = 3;
        }
      }
      function flushSpawnedWork() {
        if (4 === pendingEffectsStatus || 3 === pendingEffectsStatus) {
          pendingEffectsStatus = 0;
          requestPaint();
          var root2 = pendingEffectsRoot, finishedWork = pendingFinishedWork, lanes = pendingEffectsLanes, recoverableErrors = pendingRecoverableErrors;
          0 !== (finishedWork.subtreeFlags & 10256) || 0 !== (finishedWork.flags & 10256) ? pendingEffectsStatus = 5 : (pendingEffectsStatus = 0, pendingFinishedWork = pendingEffectsRoot = null, releaseRootPooledCache(root2, root2.pendingLanes));
          var remainingLanes = root2.pendingLanes;
          0 === remainingLanes && (legacyErrorBoundariesThatAlreadyFailed = null);
          lanesToEventPriority(lanes);
          finishedWork = finishedWork.stateNode;
          if (injectedHook && "function" === typeof injectedHook.onCommitFiberRoot)
            try {
              injectedHook.onCommitFiberRoot(
                rendererID,
                finishedWork,
                void 0,
                128 === (finishedWork.current.flags & 128)
              );
            } catch (err) {
            }
          if (null !== recoverableErrors) {
            finishedWork = ReactSharedInternals.T;
            remainingLanes = ReactDOMSharedInternals.p;
            ReactDOMSharedInternals.p = 2;
            ReactSharedInternals.T = null;
            try {
              for (var onRecoverableError = root2.onRecoverableError, i = 0; i < recoverableErrors.length; i++) {
                var recoverableError = recoverableErrors[i];
                onRecoverableError(recoverableError.value, {
                  componentStack: recoverableError.stack
                });
              }
            } finally {
              ReactSharedInternals.T = finishedWork, ReactDOMSharedInternals.p = remainingLanes;
            }
          }
          0 !== (pendingEffectsLanes & 3) && flushPendingEffects();
          ensureRootIsScheduled(root2);
          remainingLanes = root2.pendingLanes;
          0 !== (lanes & 261930) && 0 !== (remainingLanes & 42) ? root2 === rootWithNestedUpdates ? nestedUpdateCount++ : (nestedUpdateCount = 0, rootWithNestedUpdates = root2) : nestedUpdateCount = 0;
          flushSyncWorkAcrossRoots_impl(0, false);
        }
      }
      function releaseRootPooledCache(root2, remainingLanes) {
        0 === (root2.pooledCacheLanes &= remainingLanes) && (remainingLanes = root2.pooledCache, null != remainingLanes && (root2.pooledCache = null, releaseCache(remainingLanes)));
      }
      function flushPendingEffects() {
        flushMutationEffects();
        flushLayoutEffects();
        flushSpawnedWork();
        return flushPassiveEffects();
      }
      function flushPassiveEffects() {
        if (5 !== pendingEffectsStatus) return false;
        var root2 = pendingEffectsRoot, remainingLanes = pendingEffectsRemainingLanes;
        pendingEffectsRemainingLanes = 0;
        var renderPriority = lanesToEventPriority(pendingEffectsLanes), prevTransition = ReactSharedInternals.T, previousPriority = ReactDOMSharedInternals.p;
        try {
          ReactDOMSharedInternals.p = 32 > renderPriority ? 32 : renderPriority;
          ReactSharedInternals.T = null;
          renderPriority = pendingPassiveTransitions;
          pendingPassiveTransitions = null;
          var root$jscomp$0 = pendingEffectsRoot, lanes = pendingEffectsLanes;
          pendingEffectsStatus = 0;
          pendingFinishedWork = pendingEffectsRoot = null;
          pendingEffectsLanes = 0;
          if (0 !== (executionContext & 6)) throw Error(formatProdErrorMessage(331));
          var prevExecutionContext = executionContext;
          executionContext |= 4;
          commitPassiveUnmountOnFiber(root$jscomp$0.current);
          commitPassiveMountOnFiber(
            root$jscomp$0,
            root$jscomp$0.current,
            lanes,
            renderPriority
          );
          executionContext = prevExecutionContext;
          flushSyncWorkAcrossRoots_impl(0, false);
          if (injectedHook && "function" === typeof injectedHook.onPostCommitFiberRoot)
            try {
              injectedHook.onPostCommitFiberRoot(rendererID, root$jscomp$0);
            } catch (err) {
            }
          return true;
        } finally {
          ReactDOMSharedInternals.p = previousPriority, ReactSharedInternals.T = prevTransition, releaseRootPooledCache(root2, remainingLanes);
        }
      }
      function captureCommitPhaseErrorOnRoot(rootFiber, sourceFiber, error) {
        sourceFiber = createCapturedValueAtFiber(error, sourceFiber);
        sourceFiber = createRootErrorUpdate(rootFiber.stateNode, sourceFiber, 2);
        rootFiber = enqueueUpdate(rootFiber, sourceFiber, 2);
        null !== rootFiber && (markRootUpdated$1(rootFiber, 2), ensureRootIsScheduled(rootFiber));
      }
      function captureCommitPhaseError(sourceFiber, nearestMountedAncestor, error) {
        if (3 === sourceFiber.tag)
          captureCommitPhaseErrorOnRoot(sourceFiber, sourceFiber, error);
        else
          for (; null !== nearestMountedAncestor; ) {
            if (3 === nearestMountedAncestor.tag) {
              captureCommitPhaseErrorOnRoot(
                nearestMountedAncestor,
                sourceFiber,
                error
              );
              break;
            } else if (1 === nearestMountedAncestor.tag) {
              var instance = nearestMountedAncestor.stateNode;
              if ("function" === typeof nearestMountedAncestor.type.getDerivedStateFromError || "function" === typeof instance.componentDidCatch && (null === legacyErrorBoundariesThatAlreadyFailed || !legacyErrorBoundariesThatAlreadyFailed.has(instance))) {
                sourceFiber = createCapturedValueAtFiber(error, sourceFiber);
                error = createClassErrorUpdate(2);
                instance = enqueueUpdate(nearestMountedAncestor, error, 2);
                null !== instance && (initializeClassErrorUpdate(
                  error,
                  instance,
                  nearestMountedAncestor,
                  sourceFiber
                ), markRootUpdated$1(instance, 2), ensureRootIsScheduled(instance));
                break;
              }
            }
            nearestMountedAncestor = nearestMountedAncestor.return;
          }
      }
      function attachPingListener(root2, wakeable, lanes) {
        var pingCache = root2.pingCache;
        if (null === pingCache) {
          pingCache = root2.pingCache = new PossiblyWeakMap();
          var threadIDs = /* @__PURE__ */ new Set();
          pingCache.set(wakeable, threadIDs);
        } else
          threadIDs = pingCache.get(wakeable), void 0 === threadIDs && (threadIDs = /* @__PURE__ */ new Set(), pingCache.set(wakeable, threadIDs));
        threadIDs.has(lanes) || (workInProgressRootDidAttachPingListener = true, threadIDs.add(lanes), root2 = pingSuspendedRoot.bind(null, root2, wakeable, lanes), wakeable.then(root2, root2));
      }
      function pingSuspendedRoot(root2, wakeable, pingedLanes) {
        var pingCache = root2.pingCache;
        null !== pingCache && pingCache.delete(wakeable);
        root2.pingedLanes |= root2.suspendedLanes & pingedLanes;
        root2.warmLanes &= ~pingedLanes;
        workInProgressRoot === root2 && (workInProgressRootRenderLanes & pingedLanes) === pingedLanes && (4 === workInProgressRootExitStatus || 3 === workInProgressRootExitStatus && (workInProgressRootRenderLanes & 62914560) === workInProgressRootRenderLanes && 300 > now() - globalMostRecentFallbackTime ? 0 === (executionContext & 2) && prepareFreshStack(root2, 0) : workInProgressRootPingedLanes |= pingedLanes, workInProgressSuspendedRetryLanes === workInProgressRootRenderLanes && (workInProgressSuspendedRetryLanes = 0));
        ensureRootIsScheduled(root2);
      }
      function retryTimedOutBoundary(boundaryFiber, retryLane) {
        0 === retryLane && (retryLane = claimNextRetryLane());
        boundaryFiber = enqueueConcurrentRenderForLane(boundaryFiber, retryLane);
        null !== boundaryFiber && (markRootUpdated$1(boundaryFiber, retryLane), ensureRootIsScheduled(boundaryFiber));
      }
      function retryDehydratedSuspenseBoundary(boundaryFiber) {
        var suspenseState = boundaryFiber.memoizedState, retryLane = 0;
        null !== suspenseState && (retryLane = suspenseState.retryLane);
        retryTimedOutBoundary(boundaryFiber, retryLane);
      }
      function resolveRetryWakeable(boundaryFiber, wakeable) {
        var retryLane = 0;
        switch (boundaryFiber.tag) {
          case 31:
          case 13:
            var retryCache = boundaryFiber.stateNode;
            var suspenseState = boundaryFiber.memoizedState;
            null !== suspenseState && (retryLane = suspenseState.retryLane);
            break;
          case 19:
            retryCache = boundaryFiber.stateNode;
            break;
          case 22:
            retryCache = boundaryFiber.stateNode._retryCache;
            break;
          default:
            throw Error(formatProdErrorMessage(314));
        }
        null !== retryCache && retryCache.delete(wakeable);
        retryTimedOutBoundary(boundaryFiber, retryLane);
      }
      function scheduleCallback$1(priorityLevel, callback) {
        return scheduleCallback$3(priorityLevel, callback);
      }
      var firstScheduledRoot = null;
      var lastScheduledRoot = null;
      var didScheduleMicrotask = false;
      var mightHavePendingSyncWork = false;
      var isFlushingWork = false;
      var currentEventTransitionLane = 0;
      function ensureRootIsScheduled(root2) {
        root2 !== lastScheduledRoot && null === root2.next && (null === lastScheduledRoot ? firstScheduledRoot = lastScheduledRoot = root2 : lastScheduledRoot = lastScheduledRoot.next = root2);
        mightHavePendingSyncWork = true;
        didScheduleMicrotask || (didScheduleMicrotask = true, scheduleImmediateRootScheduleTask());
      }
      function flushSyncWorkAcrossRoots_impl(syncTransitionLanes, onlyLegacy) {
        if (!isFlushingWork && mightHavePendingSyncWork) {
          isFlushingWork = true;
          do {
            var didPerformSomeWork = false;
            for (var root$170 = firstScheduledRoot; null !== root$170; ) {
              if (!onlyLegacy)
                if (0 !== syncTransitionLanes) {
                  var pendingLanes = root$170.pendingLanes;
                  if (0 === pendingLanes) var JSCompiler_inline_result = 0;
                  else {
                    var suspendedLanes = root$170.suspendedLanes, pingedLanes = root$170.pingedLanes;
                    JSCompiler_inline_result = (1 << 31 - clz32(42 | syncTransitionLanes) + 1) - 1;
                    JSCompiler_inline_result &= pendingLanes & ~(suspendedLanes & ~pingedLanes);
                    JSCompiler_inline_result = JSCompiler_inline_result & 201326741 ? JSCompiler_inline_result & 201326741 | 1 : JSCompiler_inline_result ? JSCompiler_inline_result | 2 : 0;
                  }
                  0 !== JSCompiler_inline_result && (didPerformSomeWork = true, performSyncWorkOnRoot(root$170, JSCompiler_inline_result));
                } else
                  JSCompiler_inline_result = workInProgressRootRenderLanes, JSCompiler_inline_result = getNextLanes(
                    root$170,
                    root$170 === workInProgressRoot ? JSCompiler_inline_result : 0,
                    null !== root$170.cancelPendingCommit || -1 !== root$170.timeoutHandle
                  ), 0 === (JSCompiler_inline_result & 3) || checkIfRootIsPrerendering(root$170, JSCompiler_inline_result) || (didPerformSomeWork = true, performSyncWorkOnRoot(root$170, JSCompiler_inline_result));
              root$170 = root$170.next;
            }
          } while (didPerformSomeWork);
          isFlushingWork = false;
        }
      }
      function processRootScheduleInImmediateTask() {
        processRootScheduleInMicrotask();
      }
      function processRootScheduleInMicrotask() {
        mightHavePendingSyncWork = didScheduleMicrotask = false;
        var syncTransitionLanes = 0;
        0 !== currentEventTransitionLane && shouldAttemptEagerTransition() && (syncTransitionLanes = currentEventTransitionLane);
        for (var currentTime = now(), prev = null, root2 = firstScheduledRoot; null !== root2; ) {
          var next = root2.next, nextLanes = scheduleTaskForRootDuringMicrotask(root2, currentTime);
          if (0 === nextLanes)
            root2.next = null, null === prev ? firstScheduledRoot = next : prev.next = next, null === next && (lastScheduledRoot = prev);
          else if (prev = root2, 0 !== syncTransitionLanes || 0 !== (nextLanes & 3))
            mightHavePendingSyncWork = true;
          root2 = next;
        }
        0 !== pendingEffectsStatus && 5 !== pendingEffectsStatus || flushSyncWorkAcrossRoots_impl(syncTransitionLanes, false);
        0 !== currentEventTransitionLane && (currentEventTransitionLane = 0);
      }
      function scheduleTaskForRootDuringMicrotask(root2, currentTime) {
        for (var suspendedLanes = root2.suspendedLanes, pingedLanes = root2.pingedLanes, expirationTimes = root2.expirationTimes, lanes = root2.pendingLanes & -62914561; 0 < lanes; ) {
          var index$5 = 31 - clz32(lanes), lane = 1 << index$5, expirationTime = expirationTimes[index$5];
          if (-1 === expirationTime) {
            if (0 === (lane & suspendedLanes) || 0 !== (lane & pingedLanes))
              expirationTimes[index$5] = computeExpirationTime(lane, currentTime);
          } else expirationTime <= currentTime && (root2.expiredLanes |= lane);
          lanes &= ~lane;
        }
        currentTime = workInProgressRoot;
        suspendedLanes = workInProgressRootRenderLanes;
        suspendedLanes = getNextLanes(
          root2,
          root2 === currentTime ? suspendedLanes : 0,
          null !== root2.cancelPendingCommit || -1 !== root2.timeoutHandle
        );
        pingedLanes = root2.callbackNode;
        if (0 === suspendedLanes || root2 === currentTime && (2 === workInProgressSuspendedReason || 9 === workInProgressSuspendedReason) || null !== root2.cancelPendingCommit)
          return null !== pingedLanes && null !== pingedLanes && cancelCallback$1(pingedLanes), root2.callbackNode = null, root2.callbackPriority = 0;
        if (0 === (suspendedLanes & 3) || checkIfRootIsPrerendering(root2, suspendedLanes)) {
          currentTime = suspendedLanes & -suspendedLanes;
          if (currentTime === root2.callbackPriority) return currentTime;
          null !== pingedLanes && cancelCallback$1(pingedLanes);
          switch (lanesToEventPriority(suspendedLanes)) {
            case 2:
            case 8:
              suspendedLanes = UserBlockingPriority;
              break;
            case 32:
              suspendedLanes = NormalPriority$1;
              break;
            case 268435456:
              suspendedLanes = IdlePriority;
              break;
            default:
              suspendedLanes = NormalPriority$1;
          }
          pingedLanes = performWorkOnRootViaSchedulerTask.bind(null, root2);
          suspendedLanes = scheduleCallback$3(suspendedLanes, pingedLanes);
          root2.callbackPriority = currentTime;
          root2.callbackNode = suspendedLanes;
          return currentTime;
        }
        null !== pingedLanes && null !== pingedLanes && cancelCallback$1(pingedLanes);
        root2.callbackPriority = 2;
        root2.callbackNode = null;
        return 2;
      }
      function performWorkOnRootViaSchedulerTask(root2, didTimeout) {
        if (0 !== pendingEffectsStatus && 5 !== pendingEffectsStatus)
          return root2.callbackNode = null, root2.callbackPriority = 0, null;
        var originalCallbackNode = root2.callbackNode;
        if (flushPendingEffects() && root2.callbackNode !== originalCallbackNode)
          return null;
        var workInProgressRootRenderLanes$jscomp$0 = workInProgressRootRenderLanes;
        workInProgressRootRenderLanes$jscomp$0 = getNextLanes(
          root2,
          root2 === workInProgressRoot ? workInProgressRootRenderLanes$jscomp$0 : 0,
          null !== root2.cancelPendingCommit || -1 !== root2.timeoutHandle
        );
        if (0 === workInProgressRootRenderLanes$jscomp$0) return null;
        performWorkOnRoot(root2, workInProgressRootRenderLanes$jscomp$0, didTimeout);
        scheduleTaskForRootDuringMicrotask(root2, now());
        return null != root2.callbackNode && root2.callbackNode === originalCallbackNode ? performWorkOnRootViaSchedulerTask.bind(null, root2) : null;
      }
      function performSyncWorkOnRoot(root2, lanes) {
        if (flushPendingEffects()) return null;
        performWorkOnRoot(root2, lanes, true);
      }
      function scheduleImmediateRootScheduleTask() {
        scheduleMicrotask(function() {
          0 !== (executionContext & 6) ? scheduleCallback$3(
            ImmediatePriority,
            processRootScheduleInImmediateTask
          ) : processRootScheduleInMicrotask();
        });
      }
      function requestTransitionLane() {
        if (0 === currentEventTransitionLane) {
          var actionScopeLane = currentEntangledLane;
          0 === actionScopeLane && (actionScopeLane = nextTransitionUpdateLane, nextTransitionUpdateLane <<= 1, 0 === (nextTransitionUpdateLane & 261888) && (nextTransitionUpdateLane = 256));
          currentEventTransitionLane = actionScopeLane;
        }
        return currentEventTransitionLane;
      }
      function coerceFormActionProp(actionProp) {
        return null == actionProp || "symbol" === typeof actionProp || "boolean" === typeof actionProp ? null : "function" === typeof actionProp ? actionProp : sanitizeURL("" + actionProp);
      }
      function createFormDataWithSubmitter(form, submitter) {
        var temp = submitter.ownerDocument.createElement("input");
        temp.name = submitter.name;
        temp.value = submitter.value;
        form.id && temp.setAttribute("form", form.id);
        submitter.parentNode.insertBefore(temp, submitter);
        form = new FormData(form);
        temp.parentNode.removeChild(temp);
        return form;
      }
      function extractEvents$1(dispatchQueue, domEventName, maybeTargetInst, nativeEvent, nativeEventTarget) {
        if ("submit" === domEventName && maybeTargetInst && maybeTargetInst.stateNode === nativeEventTarget) {
          var action = coerceFormActionProp(
            (nativeEventTarget[internalPropsKey] || null).action
          ), submitter = nativeEvent.submitter;
          submitter && (domEventName = (domEventName = submitter[internalPropsKey] || null) ? coerceFormActionProp(domEventName.formAction) : submitter.getAttribute("formAction"), null !== domEventName && (action = domEventName, submitter = null));
          var event = new SyntheticEvent(
            "action",
            "action",
            null,
            nativeEvent,
            nativeEventTarget
          );
          dispatchQueue.push({
            event,
            listeners: [
              {
                instance: null,
                listener: function() {
                  if (nativeEvent.defaultPrevented) {
                    if (0 !== currentEventTransitionLane) {
                      var formData = submitter ? createFormDataWithSubmitter(nativeEventTarget, submitter) : new FormData(nativeEventTarget);
                      startHostTransition(
                        maybeTargetInst,
                        {
                          pending: true,
                          data: formData,
                          method: nativeEventTarget.method,
                          action
                        },
                        null,
                        formData
                      );
                    }
                  } else
                    "function" === typeof action && (event.preventDefault(), formData = submitter ? createFormDataWithSubmitter(nativeEventTarget, submitter) : new FormData(nativeEventTarget), startHostTransition(
                      maybeTargetInst,
                      {
                        pending: true,
                        data: formData,
                        method: nativeEventTarget.method,
                        action
                      },
                      action,
                      formData
                    ));
                },
                currentTarget: nativeEventTarget
              }
            ]
          });
        }
      }
      for (i$jscomp$inline_1577 = 0; i$jscomp$inline_1577 < simpleEventPluginEvents.length; i$jscomp$inline_1577++) {
        eventName$jscomp$inline_1578 = simpleEventPluginEvents[i$jscomp$inline_1577], domEventName$jscomp$inline_1579 = eventName$jscomp$inline_1578.toLowerCase(), capitalizedEvent$jscomp$inline_1580 = eventName$jscomp$inline_1578[0].toUpperCase() + eventName$jscomp$inline_1578.slice(1);
        registerSimpleEvent(
          domEventName$jscomp$inline_1579,
          "on" + capitalizedEvent$jscomp$inline_1580
        );
      }
      var eventName$jscomp$inline_1578;
      var domEventName$jscomp$inline_1579;
      var capitalizedEvent$jscomp$inline_1580;
      var i$jscomp$inline_1577;
      registerSimpleEvent(ANIMATION_END, "onAnimationEnd");
      registerSimpleEvent(ANIMATION_ITERATION, "onAnimationIteration");
      registerSimpleEvent(ANIMATION_START, "onAnimationStart");
      registerSimpleEvent("dblclick", "onDoubleClick");
      registerSimpleEvent("focusin", "onFocus");
      registerSimpleEvent("focusout", "onBlur");
      registerSimpleEvent(TRANSITION_RUN, "onTransitionRun");
      registerSimpleEvent(TRANSITION_START, "onTransitionStart");
      registerSimpleEvent(TRANSITION_CANCEL, "onTransitionCancel");
      registerSimpleEvent(TRANSITION_END, "onTransitionEnd");
      registerDirectEvent("onMouseEnter", ["mouseout", "mouseover"]);
      registerDirectEvent("onMouseLeave", ["mouseout", "mouseover"]);
      registerDirectEvent("onPointerEnter", ["pointerout", "pointerover"]);
      registerDirectEvent("onPointerLeave", ["pointerout", "pointerover"]);
      registerTwoPhaseEvent(
        "onChange",
        "change click focusin focusout input keydown keyup selectionchange".split(" ")
      );
      registerTwoPhaseEvent(
        "onSelect",
        "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(
          " "
        )
      );
      registerTwoPhaseEvent("onBeforeInput", [
        "compositionend",
        "keypress",
        "textInput",
        "paste"
      ]);
      registerTwoPhaseEvent(
        "onCompositionEnd",
        "compositionend focusout keydown keypress keyup mousedown".split(" ")
      );
      registerTwoPhaseEvent(
        "onCompositionStart",
        "compositionstart focusout keydown keypress keyup mousedown".split(" ")
      );
      registerTwoPhaseEvent(
        "onCompositionUpdate",
        "compositionupdate focusout keydown keypress keyup mousedown".split(" ")
      );
      var mediaEventTypes = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
        " "
      );
      var nonDelegatedEvents = new Set(
        "beforetoggle cancel close invalid load scroll scrollend toggle".split(" ").concat(mediaEventTypes)
      );
      function processDispatchQueue(dispatchQueue, eventSystemFlags) {
        eventSystemFlags = 0 !== (eventSystemFlags & 4);
        for (var i = 0; i < dispatchQueue.length; i++) {
          var _dispatchQueue$i = dispatchQueue[i], event = _dispatchQueue$i.event;
          _dispatchQueue$i = _dispatchQueue$i.listeners;
          a: {
            var previousInstance = void 0;
            if (eventSystemFlags)
              for (var i$jscomp$0 = _dispatchQueue$i.length - 1; 0 <= i$jscomp$0; i$jscomp$0--) {
                var _dispatchListeners$i = _dispatchQueue$i[i$jscomp$0], instance = _dispatchListeners$i.instance, currentTarget = _dispatchListeners$i.currentTarget;
                _dispatchListeners$i = _dispatchListeners$i.listener;
                if (instance !== previousInstance && event.isPropagationStopped())
                  break a;
                previousInstance = _dispatchListeners$i;
                event.currentTarget = currentTarget;
                try {
                  previousInstance(event);
                } catch (error) {
                  reportGlobalError(error);
                }
                event.currentTarget = null;
                previousInstance = instance;
              }
            else
              for (i$jscomp$0 = 0; i$jscomp$0 < _dispatchQueue$i.length; i$jscomp$0++) {
                _dispatchListeners$i = _dispatchQueue$i[i$jscomp$0];
                instance = _dispatchListeners$i.instance;
                currentTarget = _dispatchListeners$i.currentTarget;
                _dispatchListeners$i = _dispatchListeners$i.listener;
                if (instance !== previousInstance && event.isPropagationStopped())
                  break a;
                previousInstance = _dispatchListeners$i;
                event.currentTarget = currentTarget;
                try {
                  previousInstance(event);
                } catch (error) {
                  reportGlobalError(error);
                }
                event.currentTarget = null;
                previousInstance = instance;
              }
          }
        }
      }
      function listenToNonDelegatedEvent(domEventName, targetElement) {
        var JSCompiler_inline_result = targetElement[internalEventHandlersKey];
        void 0 === JSCompiler_inline_result && (JSCompiler_inline_result = targetElement[internalEventHandlersKey] = /* @__PURE__ */ new Set());
        var listenerSetKey = domEventName + "__bubble";
        JSCompiler_inline_result.has(listenerSetKey) || (addTrappedEventListener(targetElement, domEventName, 2, false), JSCompiler_inline_result.add(listenerSetKey));
      }
      function listenToNativeEvent(domEventName, isCapturePhaseListener, target) {
        var eventSystemFlags = 0;
        isCapturePhaseListener && (eventSystemFlags |= 4);
        addTrappedEventListener(
          target,
          domEventName,
          eventSystemFlags,
          isCapturePhaseListener
        );
      }
      var listeningMarker = "_reactListening" + Math.random().toString(36).slice(2);
      function listenToAllSupportedEvents(rootContainerElement) {
        if (!rootContainerElement[listeningMarker]) {
          rootContainerElement[listeningMarker] = true;
          allNativeEvents.forEach(function(domEventName) {
            "selectionchange" !== domEventName && (nonDelegatedEvents.has(domEventName) || listenToNativeEvent(domEventName, false, rootContainerElement), listenToNativeEvent(domEventName, true, rootContainerElement));
          });
          var ownerDocument = 9 === rootContainerElement.nodeType ? rootContainerElement : rootContainerElement.ownerDocument;
          null === ownerDocument || ownerDocument[listeningMarker] || (ownerDocument[listeningMarker] = true, listenToNativeEvent("selectionchange", false, ownerDocument));
        }
      }
      function addTrappedEventListener(targetContainer, domEventName, eventSystemFlags, isCapturePhaseListener) {
        switch (getEventPriority(domEventName)) {
          case 2:
            var listenerWrapper = dispatchDiscreteEvent;
            break;
          case 8:
            listenerWrapper = dispatchContinuousEvent;
            break;
          default:
            listenerWrapper = dispatchEvent;
        }
        eventSystemFlags = listenerWrapper.bind(
          null,
          domEventName,
          eventSystemFlags,
          targetContainer
        );
        listenerWrapper = void 0;
        !passiveBrowserEventsSupported || "touchstart" !== domEventName && "touchmove" !== domEventName && "wheel" !== domEventName || (listenerWrapper = true);
        isCapturePhaseListener ? void 0 !== listenerWrapper ? targetContainer.addEventListener(domEventName, eventSystemFlags, {
          capture: true,
          passive: listenerWrapper
        }) : targetContainer.addEventListener(domEventName, eventSystemFlags, true) : void 0 !== listenerWrapper ? targetContainer.addEventListener(domEventName, eventSystemFlags, {
          passive: listenerWrapper
        }) : targetContainer.addEventListener(domEventName, eventSystemFlags, false);
      }
      function dispatchEventForPluginEventSystem(domEventName, eventSystemFlags, nativeEvent, targetInst$jscomp$0, targetContainer) {
        var ancestorInst = targetInst$jscomp$0;
        if (0 === (eventSystemFlags & 1) && 0 === (eventSystemFlags & 2) && null !== targetInst$jscomp$0)
          a: for (; ; ) {
            if (null === targetInst$jscomp$0) return;
            var nodeTag = targetInst$jscomp$0.tag;
            if (3 === nodeTag || 4 === nodeTag) {
              var container = targetInst$jscomp$0.stateNode.containerInfo;
              if (container === targetContainer) break;
              if (4 === nodeTag)
                for (nodeTag = targetInst$jscomp$0.return; null !== nodeTag; ) {
                  var grandTag = nodeTag.tag;
                  if ((3 === grandTag || 4 === grandTag) && nodeTag.stateNode.containerInfo === targetContainer)
                    return;
                  nodeTag = nodeTag.return;
                }
              for (; null !== container; ) {
                nodeTag = getClosestInstanceFromNode(container);
                if (null === nodeTag) return;
                grandTag = nodeTag.tag;
                if (5 === grandTag || 6 === grandTag || 26 === grandTag || 27 === grandTag) {
                  targetInst$jscomp$0 = ancestorInst = nodeTag;
                  continue a;
                }
                container = container.parentNode;
              }
            }
            targetInst$jscomp$0 = targetInst$jscomp$0.return;
          }
        batchedUpdates$1(function() {
          var targetInst = ancestorInst, nativeEventTarget = getEventTarget(nativeEvent), dispatchQueue = [];
          a: {
            var reactName = topLevelEventsToReactNames.get(domEventName);
            if (void 0 !== reactName) {
              var SyntheticEventCtor = SyntheticEvent, reactEventType = domEventName;
              switch (domEventName) {
                case "keypress":
                  if (0 === getEventCharCode(nativeEvent)) break a;
                case "keydown":
                case "keyup":
                  SyntheticEventCtor = SyntheticKeyboardEvent;
                  break;
                case "focusin":
                  reactEventType = "focus";
                  SyntheticEventCtor = SyntheticFocusEvent;
                  break;
                case "focusout":
                  reactEventType = "blur";
                  SyntheticEventCtor = SyntheticFocusEvent;
                  break;
                case "beforeblur":
                case "afterblur":
                  SyntheticEventCtor = SyntheticFocusEvent;
                  break;
                case "click":
                  if (2 === nativeEvent.button) break a;
                case "auxclick":
                case "dblclick":
                case "mousedown":
                case "mousemove":
                case "mouseup":
                case "mouseout":
                case "mouseover":
                case "contextmenu":
                  SyntheticEventCtor = SyntheticMouseEvent;
                  break;
                case "drag":
                case "dragend":
                case "dragenter":
                case "dragexit":
                case "dragleave":
                case "dragover":
                case "dragstart":
                case "drop":
                  SyntheticEventCtor = SyntheticDragEvent;
                  break;
                case "touchcancel":
                case "touchend":
                case "touchmove":
                case "touchstart":
                  SyntheticEventCtor = SyntheticTouchEvent;
                  break;
                case ANIMATION_END:
                case ANIMATION_ITERATION:
                case ANIMATION_START:
                  SyntheticEventCtor = SyntheticAnimationEvent;
                  break;
                case TRANSITION_END:
                  SyntheticEventCtor = SyntheticTransitionEvent;
                  break;
                case "scroll":
                case "scrollend":
                  SyntheticEventCtor = SyntheticUIEvent;
                  break;
                case "wheel":
                  SyntheticEventCtor = SyntheticWheelEvent;
                  break;
                case "copy":
                case "cut":
                case "paste":
                  SyntheticEventCtor = SyntheticClipboardEvent;
                  break;
                case "gotpointercapture":
                case "lostpointercapture":
                case "pointercancel":
                case "pointerdown":
                case "pointermove":
                case "pointerout":
                case "pointerover":
                case "pointerup":
                  SyntheticEventCtor = SyntheticPointerEvent;
                  break;
                case "toggle":
                case "beforetoggle":
                  SyntheticEventCtor = SyntheticToggleEvent;
              }
              var inCapturePhase = 0 !== (eventSystemFlags & 4), accumulateTargetOnly = !inCapturePhase && ("scroll" === domEventName || "scrollend" === domEventName), reactEventName = inCapturePhase ? null !== reactName ? reactName + "Capture" : null : reactName;
              inCapturePhase = [];
              for (var instance = targetInst, lastHostComponent; null !== instance; ) {
                var _instance = instance;
                lastHostComponent = _instance.stateNode;
                _instance = _instance.tag;
                5 !== _instance && 26 !== _instance && 27 !== _instance || null === lastHostComponent || null === reactEventName || (_instance = getListener(instance, reactEventName), null != _instance && inCapturePhase.push(
                  createDispatchListener(instance, _instance, lastHostComponent)
                ));
                if (accumulateTargetOnly) break;
                instance = instance.return;
              }
              0 < inCapturePhase.length && (reactName = new SyntheticEventCtor(
                reactName,
                reactEventType,
                null,
                nativeEvent,
                nativeEventTarget
              ), dispatchQueue.push({ event: reactName, listeners: inCapturePhase }));
            }
          }
          if (0 === (eventSystemFlags & 7)) {
            a: {
              reactName = "mouseover" === domEventName || "pointerover" === domEventName;
              SyntheticEventCtor = "mouseout" === domEventName || "pointerout" === domEventName;
              if (reactName && nativeEvent !== currentReplayingEvent && (reactEventType = nativeEvent.relatedTarget || nativeEvent.fromElement) && (getClosestInstanceFromNode(reactEventType) || reactEventType[internalContainerInstanceKey]))
                break a;
              if (SyntheticEventCtor || reactName) {
                reactName = nativeEventTarget.window === nativeEventTarget ? nativeEventTarget : (reactName = nativeEventTarget.ownerDocument) ? reactName.defaultView || reactName.parentWindow : window;
                if (SyntheticEventCtor) {
                  if (reactEventType = nativeEvent.relatedTarget || nativeEvent.toElement, SyntheticEventCtor = targetInst, reactEventType = reactEventType ? getClosestInstanceFromNode(reactEventType) : null, null !== reactEventType && (accumulateTargetOnly = getNearestMountedFiber(reactEventType), inCapturePhase = reactEventType.tag, reactEventType !== accumulateTargetOnly || 5 !== inCapturePhase && 27 !== inCapturePhase && 6 !== inCapturePhase))
                    reactEventType = null;
                } else SyntheticEventCtor = null, reactEventType = targetInst;
                if (SyntheticEventCtor !== reactEventType) {
                  inCapturePhase = SyntheticMouseEvent;
                  _instance = "onMouseLeave";
                  reactEventName = "onMouseEnter";
                  instance = "mouse";
                  if ("pointerout" === domEventName || "pointerover" === domEventName)
                    inCapturePhase = SyntheticPointerEvent, _instance = "onPointerLeave", reactEventName = "onPointerEnter", instance = "pointer";
                  accumulateTargetOnly = null == SyntheticEventCtor ? reactName : getNodeFromInstance(SyntheticEventCtor);
                  lastHostComponent = null == reactEventType ? reactName : getNodeFromInstance(reactEventType);
                  reactName = new inCapturePhase(
                    _instance,
                    instance + "leave",
                    SyntheticEventCtor,
                    nativeEvent,
                    nativeEventTarget
                  );
                  reactName.target = accumulateTargetOnly;
                  reactName.relatedTarget = lastHostComponent;
                  _instance = null;
                  getClosestInstanceFromNode(nativeEventTarget) === targetInst && (inCapturePhase = new inCapturePhase(
                    reactEventName,
                    instance + "enter",
                    reactEventType,
                    nativeEvent,
                    nativeEventTarget
                  ), inCapturePhase.target = lastHostComponent, inCapturePhase.relatedTarget = accumulateTargetOnly, _instance = inCapturePhase);
                  accumulateTargetOnly = _instance;
                  if (SyntheticEventCtor && reactEventType)
                    b: {
                      inCapturePhase = getParent;
                      reactEventName = SyntheticEventCtor;
                      instance = reactEventType;
                      lastHostComponent = 0;
                      for (_instance = reactEventName; _instance; _instance = inCapturePhase(_instance))
                        lastHostComponent++;
                      _instance = 0;
                      for (var tempB = instance; tempB; tempB = inCapturePhase(tempB))
                        _instance++;
                      for (; 0 < lastHostComponent - _instance; )
                        reactEventName = inCapturePhase(reactEventName), lastHostComponent--;
                      for (; 0 < _instance - lastHostComponent; )
                        instance = inCapturePhase(instance), _instance--;
                      for (; lastHostComponent--; ) {
                        if (reactEventName === instance || null !== instance && reactEventName === instance.alternate) {
                          inCapturePhase = reactEventName;
                          break b;
                        }
                        reactEventName = inCapturePhase(reactEventName);
                        instance = inCapturePhase(instance);
                      }
                      inCapturePhase = null;
                    }
                  else inCapturePhase = null;
                  null !== SyntheticEventCtor && accumulateEnterLeaveListenersForEvent(
                    dispatchQueue,
                    reactName,
                    SyntheticEventCtor,
                    inCapturePhase,
                    false
                  );
                  null !== reactEventType && null !== accumulateTargetOnly && accumulateEnterLeaveListenersForEvent(
                    dispatchQueue,
                    accumulateTargetOnly,
                    reactEventType,
                    inCapturePhase,
                    true
                  );
                }
              }
            }
            a: {
              reactName = targetInst ? getNodeFromInstance(targetInst) : window;
              SyntheticEventCtor = reactName.nodeName && reactName.nodeName.toLowerCase();
              if ("select" === SyntheticEventCtor || "input" === SyntheticEventCtor && "file" === reactName.type)
                var getTargetInstFunc = getTargetInstForChangeEvent;
              else if (isTextInputElement(reactName))
                if (isInputEventSupported)
                  getTargetInstFunc = getTargetInstForInputOrChangeEvent;
                else {
                  getTargetInstFunc = getTargetInstForInputEventPolyfill;
                  var handleEventFunc = handleEventsForInputEventPolyfill;
                }
              else
                SyntheticEventCtor = reactName.nodeName, !SyntheticEventCtor || "input" !== SyntheticEventCtor.toLowerCase() || "checkbox" !== reactName.type && "radio" !== reactName.type ? targetInst && isCustomElement(targetInst.elementType) && (getTargetInstFunc = getTargetInstForChangeEvent) : getTargetInstFunc = getTargetInstForClickEvent;
              if (getTargetInstFunc && (getTargetInstFunc = getTargetInstFunc(domEventName, targetInst))) {
                createAndAccumulateChangeEvent(
                  dispatchQueue,
                  getTargetInstFunc,
                  nativeEvent,
                  nativeEventTarget
                );
                break a;
              }
              handleEventFunc && handleEventFunc(domEventName, reactName, targetInst);
              "focusout" === domEventName && targetInst && "number" === reactName.type && null != targetInst.memoizedProps.value && setDefaultValue(reactName, "number", reactName.value);
            }
            handleEventFunc = targetInst ? getNodeFromInstance(targetInst) : window;
            switch (domEventName) {
              case "focusin":
                if (isTextInputElement(handleEventFunc) || "true" === handleEventFunc.contentEditable)
                  activeElement = handleEventFunc, activeElementInst = targetInst, lastSelection = null;
                break;
              case "focusout":
                lastSelection = activeElementInst = activeElement = null;
                break;
              case "mousedown":
                mouseDown = true;
                break;
              case "contextmenu":
              case "mouseup":
              case "dragend":
                mouseDown = false;
                constructSelectEvent(dispatchQueue, nativeEvent, nativeEventTarget);
                break;
              case "selectionchange":
                if (skipSelectionChangeEvent) break;
              case "keydown":
              case "keyup":
                constructSelectEvent(dispatchQueue, nativeEvent, nativeEventTarget);
            }
            var fallbackData;
            if (canUseCompositionEvent)
              b: {
                switch (domEventName) {
                  case "compositionstart":
                    var eventType = "onCompositionStart";
                    break b;
                  case "compositionend":
                    eventType = "onCompositionEnd";
                    break b;
                  case "compositionupdate":
                    eventType = "onCompositionUpdate";
                    break b;
                }
                eventType = void 0;
              }
            else
              isComposing ? isFallbackCompositionEnd(domEventName, nativeEvent) && (eventType = "onCompositionEnd") : "keydown" === domEventName && 229 === nativeEvent.keyCode && (eventType = "onCompositionStart");
            eventType && (useFallbackCompositionData && "ko" !== nativeEvent.locale && (isComposing || "onCompositionStart" !== eventType ? "onCompositionEnd" === eventType && isComposing && (fallbackData = getData()) : (root = nativeEventTarget, startText = "value" in root ? root.value : root.textContent, isComposing = true)), handleEventFunc = accumulateTwoPhaseListeners(targetInst, eventType), 0 < handleEventFunc.length && (eventType = new SyntheticCompositionEvent(
              eventType,
              domEventName,
              null,
              nativeEvent,
              nativeEventTarget
            ), dispatchQueue.push({ event: eventType, listeners: handleEventFunc }), fallbackData ? eventType.data = fallbackData : (fallbackData = getDataFromCustomEvent(nativeEvent), null !== fallbackData && (eventType.data = fallbackData))));
            if (fallbackData = canUseTextInputEvent ? getNativeBeforeInputChars(domEventName, nativeEvent) : getFallbackBeforeInputChars(domEventName, nativeEvent))
              eventType = accumulateTwoPhaseListeners(targetInst, "onBeforeInput"), 0 < eventType.length && (handleEventFunc = new SyntheticCompositionEvent(
                "onBeforeInput",
                "beforeinput",
                null,
                nativeEvent,
                nativeEventTarget
              ), dispatchQueue.push({
                event: handleEventFunc,
                listeners: eventType
              }), handleEventFunc.data = fallbackData);
            extractEvents$1(
              dispatchQueue,
              domEventName,
              targetInst,
              nativeEvent,
              nativeEventTarget
            );
          }
          processDispatchQueue(dispatchQueue, eventSystemFlags);
        });
      }
      function createDispatchListener(instance, listener, currentTarget) {
        return {
          instance,
          listener,
          currentTarget
        };
      }
      function accumulateTwoPhaseListeners(targetFiber, reactName) {
        for (var captureName = reactName + "Capture", listeners = []; null !== targetFiber; ) {
          var _instance2 = targetFiber, stateNode = _instance2.stateNode;
          _instance2 = _instance2.tag;
          5 !== _instance2 && 26 !== _instance2 && 27 !== _instance2 || null === stateNode || (_instance2 = getListener(targetFiber, captureName), null != _instance2 && listeners.unshift(
            createDispatchListener(targetFiber, _instance2, stateNode)
          ), _instance2 = getListener(targetFiber, reactName), null != _instance2 && listeners.push(
            createDispatchListener(targetFiber, _instance2, stateNode)
          ));
          if (3 === targetFiber.tag) return listeners;
          targetFiber = targetFiber.return;
        }
        return [];
      }
      function getParent(inst) {
        if (null === inst) return null;
        do
          inst = inst.return;
        while (inst && 5 !== inst.tag && 27 !== inst.tag);
        return inst ? inst : null;
      }
      function accumulateEnterLeaveListenersForEvent(dispatchQueue, event, target, common, inCapturePhase) {
        for (var registrationName = event._reactName, listeners = []; null !== target && target !== common; ) {
          var _instance3 = target, alternate = _instance3.alternate, stateNode = _instance3.stateNode;
          _instance3 = _instance3.tag;
          if (null !== alternate && alternate === common) break;
          5 !== _instance3 && 26 !== _instance3 && 27 !== _instance3 || null === stateNode || (alternate = stateNode, inCapturePhase ? (stateNode = getListener(target, registrationName), null != stateNode && listeners.unshift(
            createDispatchListener(target, stateNode, alternate)
          )) : inCapturePhase || (stateNode = getListener(target, registrationName), null != stateNode && listeners.push(
            createDispatchListener(target, stateNode, alternate)
          )));
          target = target.return;
        }
        0 !== listeners.length && dispatchQueue.push({ event, listeners });
      }
      var NORMALIZE_NEWLINES_REGEX = /\r\n?/g;
      var NORMALIZE_NULL_AND_REPLACEMENT_REGEX = /\u0000|\uFFFD/g;
      function normalizeMarkupForTextOrAttribute(markup) {
        return ("string" === typeof markup ? markup : "" + markup).replace(NORMALIZE_NEWLINES_REGEX, "\n").replace(NORMALIZE_NULL_AND_REPLACEMENT_REGEX, "");
      }
      function checkForUnmatchedText(serverText, clientText) {
        clientText = normalizeMarkupForTextOrAttribute(clientText);
        return normalizeMarkupForTextOrAttribute(serverText) === clientText ? true : false;
      }
      function setProp(domElement, tag, key, value, props, prevValue) {
        switch (key) {
          case "children":
            "string" === typeof value ? "body" === tag || "textarea" === tag && "" === value || setTextContent(domElement, value) : ("number" === typeof value || "bigint" === typeof value) && "body" !== tag && setTextContent(domElement, "" + value);
            break;
          case "className":
            setValueForKnownAttribute(domElement, "class", value);
            break;
          case "tabIndex":
            setValueForKnownAttribute(domElement, "tabindex", value);
            break;
          case "dir":
          case "role":
          case "viewBox":
          case "width":
          case "height":
            setValueForKnownAttribute(domElement, key, value);
            break;
          case "style":
            setValueForStyles(domElement, value, prevValue);
            break;
          case "data":
            if ("object" !== tag) {
              setValueForKnownAttribute(domElement, "data", value);
              break;
            }
          case "src":
          case "href":
            if ("" === value && ("a" !== tag || "href" !== key)) {
              domElement.removeAttribute(key);
              break;
            }
            if (null == value || "function" === typeof value || "symbol" === typeof value || "boolean" === typeof value) {
              domElement.removeAttribute(key);
              break;
            }
            value = sanitizeURL("" + value);
            domElement.setAttribute(key, value);
            break;
          case "action":
          case "formAction":
            if ("function" === typeof value) {
              domElement.setAttribute(
                key,
                "javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')"
              );
              break;
            } else
              "function" === typeof prevValue && ("formAction" === key ? ("input" !== tag && setProp(domElement, tag, "name", props.name, props, null), setProp(
                domElement,
                tag,
                "formEncType",
                props.formEncType,
                props,
                null
              ), setProp(
                domElement,
                tag,
                "formMethod",
                props.formMethod,
                props,
                null
              ), setProp(
                domElement,
                tag,
                "formTarget",
                props.formTarget,
                props,
                null
              )) : (setProp(domElement, tag, "encType", props.encType, props, null), setProp(domElement, tag, "method", props.method, props, null), setProp(domElement, tag, "target", props.target, props, null)));
            if (null == value || "symbol" === typeof value || "boolean" === typeof value) {
              domElement.removeAttribute(key);
              break;
            }
            value = sanitizeURL("" + value);
            domElement.setAttribute(key, value);
            break;
          case "onClick":
            null != value && (domElement.onclick = noop$1);
            break;
          case "onScroll":
            null != value && listenToNonDelegatedEvent("scroll", domElement);
            break;
          case "onScrollEnd":
            null != value && listenToNonDelegatedEvent("scrollend", domElement);
            break;
          case "dangerouslySetInnerHTML":
            if (null != value) {
              if ("object" !== typeof value || !("__html" in value))
                throw Error(formatProdErrorMessage(61));
              key = value.__html;
              if (null != key) {
                if (null != props.children) throw Error(formatProdErrorMessage(60));
                domElement.innerHTML = key;
              }
            }
            break;
          case "multiple":
            domElement.multiple = value && "function" !== typeof value && "symbol" !== typeof value;
            break;
          case "muted":
            domElement.muted = value && "function" !== typeof value && "symbol" !== typeof value;
            break;
          case "suppressContentEditableWarning":
          case "suppressHydrationWarning":
          case "defaultValue":
          case "defaultChecked":
          case "innerHTML":
          case "ref":
            break;
          case "autoFocus":
            break;
          case "xlinkHref":
            if (null == value || "function" === typeof value || "boolean" === typeof value || "symbol" === typeof value) {
              domElement.removeAttribute("xlink:href");
              break;
            }
            key = sanitizeURL("" + value);
            domElement.setAttributeNS(
              "http://www.w3.org/1999/xlink",
              "xlink:href",
              key
            );
            break;
          case "contentEditable":
          case "spellCheck":
          case "draggable":
          case "value":
          case "autoReverse":
          case "externalResourcesRequired":
          case "focusable":
          case "preserveAlpha":
            null != value && "function" !== typeof value && "symbol" !== typeof value ? domElement.setAttribute(key, "" + value) : domElement.removeAttribute(key);
            break;
          case "inert":
          case "allowFullScreen":
          case "async":
          case "autoPlay":
          case "controls":
          case "default":
          case "defer":
          case "disabled":
          case "disablePictureInPicture":
          case "disableRemotePlayback":
          case "formNoValidate":
          case "hidden":
          case "loop":
          case "noModule":
          case "noValidate":
          case "open":
          case "playsInline":
          case "readOnly":
          case "required":
          case "reversed":
          case "scoped":
          case "seamless":
          case "itemScope":
            value && "function" !== typeof value && "symbol" !== typeof value ? domElement.setAttribute(key, "") : domElement.removeAttribute(key);
            break;
          case "capture":
          case "download":
            true === value ? domElement.setAttribute(key, "") : false !== value && null != value && "function" !== typeof value && "symbol" !== typeof value ? domElement.setAttribute(key, value) : domElement.removeAttribute(key);
            break;
          case "cols":
          case "rows":
          case "size":
          case "span":
            null != value && "function" !== typeof value && "symbol" !== typeof value && !isNaN(value) && 1 <= value ? domElement.setAttribute(key, value) : domElement.removeAttribute(key);
            break;
          case "rowSpan":
          case "start":
            null == value || "function" === typeof value || "symbol" === typeof value || isNaN(value) ? domElement.removeAttribute(key) : domElement.setAttribute(key, value);
            break;
          case "popover":
            listenToNonDelegatedEvent("beforetoggle", domElement);
            listenToNonDelegatedEvent("toggle", domElement);
            setValueForAttribute(domElement, "popover", value);
            break;
          case "xlinkActuate":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:actuate",
              value
            );
            break;
          case "xlinkArcrole":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:arcrole",
              value
            );
            break;
          case "xlinkRole":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:role",
              value
            );
            break;
          case "xlinkShow":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:show",
              value
            );
            break;
          case "xlinkTitle":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:title",
              value
            );
            break;
          case "xlinkType":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/1999/xlink",
              "xlink:type",
              value
            );
            break;
          case "xmlBase":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/XML/1998/namespace",
              "xml:base",
              value
            );
            break;
          case "xmlLang":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/XML/1998/namespace",
              "xml:lang",
              value
            );
            break;
          case "xmlSpace":
            setValueForNamespacedAttribute(
              domElement,
              "http://www.w3.org/XML/1998/namespace",
              "xml:space",
              value
            );
            break;
          case "is":
            setValueForAttribute(domElement, "is", value);
            break;
          case "innerText":
          case "textContent":
            break;
          default:
            if (!(2 < key.length) || "o" !== key[0] && "O" !== key[0] || "n" !== key[1] && "N" !== key[1])
              key = aliases.get(key) || key, setValueForAttribute(domElement, key, value);
        }
      }
      function setPropOnCustomElement(domElement, tag, key, value, props, prevValue) {
        switch (key) {
          case "style":
            setValueForStyles(domElement, value, prevValue);
            break;
          case "dangerouslySetInnerHTML":
            if (null != value) {
              if ("object" !== typeof value || !("__html" in value))
                throw Error(formatProdErrorMessage(61));
              key = value.__html;
              if (null != key) {
                if (null != props.children) throw Error(formatProdErrorMessage(60));
                domElement.innerHTML = key;
              }
            }
            break;
          case "children":
            "string" === typeof value ? setTextContent(domElement, value) : ("number" === typeof value || "bigint" === typeof value) && setTextContent(domElement, "" + value);
            break;
          case "onScroll":
            null != value && listenToNonDelegatedEvent("scroll", domElement);
            break;
          case "onScrollEnd":
            null != value && listenToNonDelegatedEvent("scrollend", domElement);
            break;
          case "onClick":
            null != value && (domElement.onclick = noop$1);
            break;
          case "suppressContentEditableWarning":
          case "suppressHydrationWarning":
          case "innerHTML":
          case "ref":
            break;
          case "innerText":
          case "textContent":
            break;
          default:
            if (!registrationNameDependencies.hasOwnProperty(key))
              a: {
                if ("o" === key[0] && "n" === key[1] && (props = key.endsWith("Capture"), tag = key.slice(2, props ? key.length - 7 : void 0), prevValue = domElement[internalPropsKey] || null, prevValue = null != prevValue ? prevValue[key] : null, "function" === typeof prevValue && domElement.removeEventListener(tag, prevValue, props), "function" === typeof value)) {
                  "function" !== typeof prevValue && null !== prevValue && (key in domElement ? domElement[key] = null : domElement.hasAttribute(key) && domElement.removeAttribute(key));
                  domElement.addEventListener(tag, value, props);
                  break a;
                }
                key in domElement ? domElement[key] = value : true === value ? domElement.setAttribute(key, "") : setValueForAttribute(domElement, key, value);
              }
        }
      }
      function setInitialProperties(domElement, tag, props) {
        switch (tag) {
          case "div":
          case "span":
          case "svg":
          case "path":
          case "a":
          case "g":
          case "p":
          case "li":
            break;
          case "img":
            listenToNonDelegatedEvent("error", domElement);
            listenToNonDelegatedEvent("load", domElement);
            var hasSrc = false, hasSrcSet = false, propKey;
            for (propKey in props)
              if (props.hasOwnProperty(propKey)) {
                var propValue = props[propKey];
                if (null != propValue)
                  switch (propKey) {
                    case "src":
                      hasSrc = true;
                      break;
                    case "srcSet":
                      hasSrcSet = true;
                      break;
                    case "children":
                    case "dangerouslySetInnerHTML":
                      throw Error(formatProdErrorMessage(137, tag));
                    default:
                      setProp(domElement, tag, propKey, propValue, props, null);
                  }
              }
            hasSrcSet && setProp(domElement, tag, "srcSet", props.srcSet, props, null);
            hasSrc && setProp(domElement, tag, "src", props.src, props, null);
            return;
          case "input":
            listenToNonDelegatedEvent("invalid", domElement);
            var defaultValue = propKey = propValue = hasSrcSet = null, checked = null, defaultChecked = null;
            for (hasSrc in props)
              if (props.hasOwnProperty(hasSrc)) {
                var propValue$184 = props[hasSrc];
                if (null != propValue$184)
                  switch (hasSrc) {
                    case "name":
                      hasSrcSet = propValue$184;
                      break;
                    case "type":
                      propValue = propValue$184;
                      break;
                    case "checked":
                      checked = propValue$184;
                      break;
                    case "defaultChecked":
                      defaultChecked = propValue$184;
                      break;
                    case "value":
                      propKey = propValue$184;
                      break;
                    case "defaultValue":
                      defaultValue = propValue$184;
                      break;
                    case "children":
                    case "dangerouslySetInnerHTML":
                      if (null != propValue$184)
                        throw Error(formatProdErrorMessage(137, tag));
                      break;
                    default:
                      setProp(domElement, tag, hasSrc, propValue$184, props, null);
                  }
              }
            initInput(
              domElement,
              propKey,
              defaultValue,
              checked,
              defaultChecked,
              propValue,
              hasSrcSet,
              false
            );
            return;
          case "select":
            listenToNonDelegatedEvent("invalid", domElement);
            hasSrc = propValue = propKey = null;
            for (hasSrcSet in props)
              if (props.hasOwnProperty(hasSrcSet) && (defaultValue = props[hasSrcSet], null != defaultValue))
                switch (hasSrcSet) {
                  case "value":
                    propKey = defaultValue;
                    break;
                  case "defaultValue":
                    propValue = defaultValue;
                    break;
                  case "multiple":
                    hasSrc = defaultValue;
                  default:
                    setProp(domElement, tag, hasSrcSet, defaultValue, props, null);
                }
            tag = propKey;
            props = propValue;
            domElement.multiple = !!hasSrc;
            null != tag ? updateOptions(domElement, !!hasSrc, tag, false) : null != props && updateOptions(domElement, !!hasSrc, props, true);
            return;
          case "textarea":
            listenToNonDelegatedEvent("invalid", domElement);
            propKey = hasSrcSet = hasSrc = null;
            for (propValue in props)
              if (props.hasOwnProperty(propValue) && (defaultValue = props[propValue], null != defaultValue))
                switch (propValue) {
                  case "value":
                    hasSrc = defaultValue;
                    break;
                  case "defaultValue":
                    hasSrcSet = defaultValue;
                    break;
                  case "children":
                    propKey = defaultValue;
                    break;
                  case "dangerouslySetInnerHTML":
                    if (null != defaultValue) throw Error(formatProdErrorMessage(91));
                    break;
                  default:
                    setProp(domElement, tag, propValue, defaultValue, props, null);
                }
            initTextarea(domElement, hasSrc, hasSrcSet, propKey);
            return;
          case "option":
            for (checked in props)
              if (props.hasOwnProperty(checked) && (hasSrc = props[checked], null != hasSrc))
                switch (checked) {
                  case "selected":
                    domElement.selected = hasSrc && "function" !== typeof hasSrc && "symbol" !== typeof hasSrc;
                    break;
                  default:
                    setProp(domElement, tag, checked, hasSrc, props, null);
                }
            return;
          case "dialog":
            listenToNonDelegatedEvent("beforetoggle", domElement);
            listenToNonDelegatedEvent("toggle", domElement);
            listenToNonDelegatedEvent("cancel", domElement);
            listenToNonDelegatedEvent("close", domElement);
            break;
          case "iframe":
          case "object":
            listenToNonDelegatedEvent("load", domElement);
            break;
          case "video":
          case "audio":
            for (hasSrc = 0; hasSrc < mediaEventTypes.length; hasSrc++)
              listenToNonDelegatedEvent(mediaEventTypes[hasSrc], domElement);
            break;
          case "image":
            listenToNonDelegatedEvent("error", domElement);
            listenToNonDelegatedEvent("load", domElement);
            break;
          case "details":
            listenToNonDelegatedEvent("toggle", domElement);
            break;
          case "embed":
          case "source":
          case "link":
            listenToNonDelegatedEvent("error", domElement), listenToNonDelegatedEvent("load", domElement);
          case "area":
          case "base":
          case "br":
          case "col":
          case "hr":
          case "keygen":
          case "meta":
          case "param":
          case "track":
          case "wbr":
          case "menuitem":
            for (defaultChecked in props)
              if (props.hasOwnProperty(defaultChecked) && (hasSrc = props[defaultChecked], null != hasSrc))
                switch (defaultChecked) {
                  case "children":
                  case "dangerouslySetInnerHTML":
                    throw Error(formatProdErrorMessage(137, tag));
                  default:
                    setProp(domElement, tag, defaultChecked, hasSrc, props, null);
                }
            return;
          default:
            if (isCustomElement(tag)) {
              for (propValue$184 in props)
                props.hasOwnProperty(propValue$184) && (hasSrc = props[propValue$184], void 0 !== hasSrc && setPropOnCustomElement(
                  domElement,
                  tag,
                  propValue$184,
                  hasSrc,
                  props,
                  void 0
                ));
              return;
            }
        }
        for (defaultValue in props)
          props.hasOwnProperty(defaultValue) && (hasSrc = props[defaultValue], null != hasSrc && setProp(domElement, tag, defaultValue, hasSrc, props, null));
      }
      function updateProperties(domElement, tag, lastProps, nextProps) {
        switch (tag) {
          case "div":
          case "span":
          case "svg":
          case "path":
          case "a":
          case "g":
          case "p":
          case "li":
            break;
          case "input":
            var name = null, type = null, value = null, defaultValue = null, lastDefaultValue = null, checked = null, defaultChecked = null;
            for (propKey in lastProps) {
              var lastProp = lastProps[propKey];
              if (lastProps.hasOwnProperty(propKey) && null != lastProp)
                switch (propKey) {
                  case "checked":
                    break;
                  case "value":
                    break;
                  case "defaultValue":
                    lastDefaultValue = lastProp;
                  default:
                    nextProps.hasOwnProperty(propKey) || setProp(domElement, tag, propKey, null, nextProps, lastProp);
                }
            }
            for (var propKey$201 in nextProps) {
              var propKey = nextProps[propKey$201];
              lastProp = lastProps[propKey$201];
              if (nextProps.hasOwnProperty(propKey$201) && (null != propKey || null != lastProp))
                switch (propKey$201) {
                  case "type":
                    type = propKey;
                    break;
                  case "name":
                    name = propKey;
                    break;
                  case "checked":
                    checked = propKey;
                    break;
                  case "defaultChecked":
                    defaultChecked = propKey;
                    break;
                  case "value":
                    value = propKey;
                    break;
                  case "defaultValue":
                    defaultValue = propKey;
                    break;
                  case "children":
                  case "dangerouslySetInnerHTML":
                    if (null != propKey)
                      throw Error(formatProdErrorMessage(137, tag));
                    break;
                  default:
                    propKey !== lastProp && setProp(
                      domElement,
                      tag,
                      propKey$201,
                      propKey,
                      nextProps,
                      lastProp
                    );
                }
            }
            updateInput(
              domElement,
              value,
              defaultValue,
              lastDefaultValue,
              checked,
              defaultChecked,
              type,
              name
            );
            return;
          case "select":
            propKey = value = defaultValue = propKey$201 = null;
            for (type in lastProps)
              if (lastDefaultValue = lastProps[type], lastProps.hasOwnProperty(type) && null != lastDefaultValue)
                switch (type) {
                  case "value":
                    break;
                  case "multiple":
                    propKey = lastDefaultValue;
                  default:
                    nextProps.hasOwnProperty(type) || setProp(
                      domElement,
                      tag,
                      type,
                      null,
                      nextProps,
                      lastDefaultValue
                    );
                }
            for (name in nextProps)
              if (type = nextProps[name], lastDefaultValue = lastProps[name], nextProps.hasOwnProperty(name) && (null != type || null != lastDefaultValue))
                switch (name) {
                  case "value":
                    propKey$201 = type;
                    break;
                  case "defaultValue":
                    defaultValue = type;
                    break;
                  case "multiple":
                    value = type;
                  default:
                    type !== lastDefaultValue && setProp(
                      domElement,
                      tag,
                      name,
                      type,
                      nextProps,
                      lastDefaultValue
                    );
                }
            tag = defaultValue;
            lastProps = value;
            nextProps = propKey;
            null != propKey$201 ? updateOptions(domElement, !!lastProps, propKey$201, false) : !!nextProps !== !!lastProps && (null != tag ? updateOptions(domElement, !!lastProps, tag, true) : updateOptions(domElement, !!lastProps, lastProps ? [] : "", false));
            return;
          case "textarea":
            propKey = propKey$201 = null;
            for (defaultValue in lastProps)
              if (name = lastProps[defaultValue], lastProps.hasOwnProperty(defaultValue) && null != name && !nextProps.hasOwnProperty(defaultValue))
                switch (defaultValue) {
                  case "value":
                    break;
                  case "children":
                    break;
                  default:
                    setProp(domElement, tag, defaultValue, null, nextProps, name);
                }
            for (value in nextProps)
              if (name = nextProps[value], type = lastProps[value], nextProps.hasOwnProperty(value) && (null != name || null != type))
                switch (value) {
                  case "value":
                    propKey$201 = name;
                    break;
                  case "defaultValue":
                    propKey = name;
                    break;
                  case "children":
                    break;
                  case "dangerouslySetInnerHTML":
                    if (null != name) throw Error(formatProdErrorMessage(91));
                    break;
                  default:
                    name !== type && setProp(domElement, tag, value, name, nextProps, type);
                }
            updateTextarea(domElement, propKey$201, propKey);
            return;
          case "option":
            for (var propKey$217 in lastProps)
              if (propKey$201 = lastProps[propKey$217], lastProps.hasOwnProperty(propKey$217) && null != propKey$201 && !nextProps.hasOwnProperty(propKey$217))
                switch (propKey$217) {
                  case "selected":
                    domElement.selected = false;
                    break;
                  default:
                    setProp(
                      domElement,
                      tag,
                      propKey$217,
                      null,
                      nextProps,
                      propKey$201
                    );
                }
            for (lastDefaultValue in nextProps)
              if (propKey$201 = nextProps[lastDefaultValue], propKey = lastProps[lastDefaultValue], nextProps.hasOwnProperty(lastDefaultValue) && propKey$201 !== propKey && (null != propKey$201 || null != propKey))
                switch (lastDefaultValue) {
                  case "selected":
                    domElement.selected = propKey$201 && "function" !== typeof propKey$201 && "symbol" !== typeof propKey$201;
                    break;
                  default:
                    setProp(
                      domElement,
                      tag,
                      lastDefaultValue,
                      propKey$201,
                      nextProps,
                      propKey
                    );
                }
            return;
          case "img":
          case "link":
          case "area":
          case "base":
          case "br":
          case "col":
          case "embed":
          case "hr":
          case "keygen":
          case "meta":
          case "param":
          case "source":
          case "track":
          case "wbr":
          case "menuitem":
            for (var propKey$222 in lastProps)
              propKey$201 = lastProps[propKey$222], lastProps.hasOwnProperty(propKey$222) && null != propKey$201 && !nextProps.hasOwnProperty(propKey$222) && setProp(domElement, tag, propKey$222, null, nextProps, propKey$201);
            for (checked in nextProps)
              if (propKey$201 = nextProps[checked], propKey = lastProps[checked], nextProps.hasOwnProperty(checked) && propKey$201 !== propKey && (null != propKey$201 || null != propKey))
                switch (checked) {
                  case "children":
                  case "dangerouslySetInnerHTML":
                    if (null != propKey$201)
                      throw Error(formatProdErrorMessage(137, tag));
                    break;
                  default:
                    setProp(
                      domElement,
                      tag,
                      checked,
                      propKey$201,
                      nextProps,
                      propKey
                    );
                }
            return;
          default:
            if (isCustomElement(tag)) {
              for (var propKey$227 in lastProps)
                propKey$201 = lastProps[propKey$227], lastProps.hasOwnProperty(propKey$227) && void 0 !== propKey$201 && !nextProps.hasOwnProperty(propKey$227) && setPropOnCustomElement(
                  domElement,
                  tag,
                  propKey$227,
                  void 0,
                  nextProps,
                  propKey$201
                );
              for (defaultChecked in nextProps)
                propKey$201 = nextProps[defaultChecked], propKey = lastProps[defaultChecked], !nextProps.hasOwnProperty(defaultChecked) || propKey$201 === propKey || void 0 === propKey$201 && void 0 === propKey || setPropOnCustomElement(
                  domElement,
                  tag,
                  defaultChecked,
                  propKey$201,
                  nextProps,
                  propKey
                );
              return;
            }
        }
        for (var propKey$232 in lastProps)
          propKey$201 = lastProps[propKey$232], lastProps.hasOwnProperty(propKey$232) && null != propKey$201 && !nextProps.hasOwnProperty(propKey$232) && setProp(domElement, tag, propKey$232, null, nextProps, propKey$201);
        for (lastProp in nextProps)
          propKey$201 = nextProps[lastProp], propKey = lastProps[lastProp], !nextProps.hasOwnProperty(lastProp) || propKey$201 === propKey || null == propKey$201 && null == propKey || setProp(domElement, tag, lastProp, propKey$201, nextProps, propKey);
      }
      function isLikelyStaticResource(initiatorType) {
        switch (initiatorType) {
          case "css":
          case "script":
          case "font":
          case "img":
          case "image":
          case "input":
          case "link":
            return true;
          default:
            return false;
        }
      }
      function estimateBandwidth() {
        if ("function" === typeof performance.getEntriesByType) {
          for (var count = 0, bits = 0, resourceEntries = performance.getEntriesByType("resource"), i = 0; i < resourceEntries.length; i++) {
            var entry = resourceEntries[i], transferSize = entry.transferSize, initiatorType = entry.initiatorType, duration = entry.duration;
            if (transferSize && duration && isLikelyStaticResource(initiatorType)) {
              initiatorType = 0;
              duration = entry.responseEnd;
              for (i += 1; i < resourceEntries.length; i++) {
                var overlapEntry = resourceEntries[i], overlapStartTime = overlapEntry.startTime;
                if (overlapStartTime > duration) break;
                var overlapTransferSize = overlapEntry.transferSize, overlapInitiatorType = overlapEntry.initiatorType;
                overlapTransferSize && isLikelyStaticResource(overlapInitiatorType) && (overlapEntry = overlapEntry.responseEnd, initiatorType += overlapTransferSize * (overlapEntry < duration ? 1 : (duration - overlapStartTime) / (overlapEntry - overlapStartTime)));
              }
              --i;
              bits += 8 * (transferSize + initiatorType) / (entry.duration / 1e3);
              count++;
              if (10 < count) break;
            }
          }
          if (0 < count) return bits / count / 1e6;
        }
        return navigator.connection && (count = navigator.connection.downlink, "number" === typeof count) ? count : 5;
      }
      var eventsEnabled = null;
      var selectionInformation = null;
      function getOwnerDocumentFromRootContainer(rootContainerElement) {
        return 9 === rootContainerElement.nodeType ? rootContainerElement : rootContainerElement.ownerDocument;
      }
      function getOwnHostContext(namespaceURI) {
        switch (namespaceURI) {
          case "http://www.w3.org/2000/svg":
            return 1;
          case "http://www.w3.org/1998/Math/MathML":
            return 2;
          default:
            return 0;
        }
      }
      function getChildHostContextProd(parentNamespace, type) {
        if (0 === parentNamespace)
          switch (type) {
            case "svg":
              return 1;
            case "math":
              return 2;
            default:
              return 0;
          }
        return 1 === parentNamespace && "foreignObject" === type ? 0 : parentNamespace;
      }
      function shouldSetTextContent(type, props) {
        return "textarea" === type || "noscript" === type || "string" === typeof props.children || "number" === typeof props.children || "bigint" === typeof props.children || "object" === typeof props.dangerouslySetInnerHTML && null !== props.dangerouslySetInnerHTML && null != props.dangerouslySetInnerHTML.__html;
      }
      var currentPopstateTransitionEvent = null;
      function shouldAttemptEagerTransition() {
        var event = window.event;
        if (event && "popstate" === event.type) {
          if (event === currentPopstateTransitionEvent) return false;
          currentPopstateTransitionEvent = event;
          return true;
        }
        currentPopstateTransitionEvent = null;
        return false;
      }
      var scheduleTimeout = "function" === typeof setTimeout ? setTimeout : void 0;
      var cancelTimeout = "function" === typeof clearTimeout ? clearTimeout : void 0;
      var localPromise = "function" === typeof Promise ? Promise : void 0;
      var scheduleMicrotask = "function" === typeof queueMicrotask ? queueMicrotask : "undefined" !== typeof localPromise ? function(callback) {
        return localPromise.resolve(null).then(callback).catch(handleErrorInNextTick);
      } : scheduleTimeout;
      function handleErrorInNextTick(error) {
        setTimeout(function() {
          throw error;
        });
      }
      function isSingletonScope(type) {
        return "head" === type;
      }
      function clearHydrationBoundary(parentInstance, hydrationInstance) {
        var node = hydrationInstance, depth = 0;
        do {
          var nextNode = node.nextSibling;
          parentInstance.removeChild(node);
          if (nextNode && 8 === nextNode.nodeType)
            if (node = nextNode.data, "/$" === node || "/&" === node) {
              if (0 === depth) {
                parentInstance.removeChild(nextNode);
                retryIfBlockedOn(hydrationInstance);
                return;
              }
              depth--;
            } else if ("$" === node || "$?" === node || "$~" === node || "$!" === node || "&" === node)
              depth++;
            else if ("html" === node)
              releaseSingletonInstance(parentInstance.ownerDocument.documentElement);
            else if ("head" === node) {
              node = parentInstance.ownerDocument.head;
              releaseSingletonInstance(node);
              for (var node$jscomp$0 = node.firstChild; node$jscomp$0; ) {
                var nextNode$jscomp$0 = node$jscomp$0.nextSibling, nodeName = node$jscomp$0.nodeName;
                node$jscomp$0[internalHoistableMarker] || "SCRIPT" === nodeName || "STYLE" === nodeName || "LINK" === nodeName && "stylesheet" === node$jscomp$0.rel.toLowerCase() || node.removeChild(node$jscomp$0);
                node$jscomp$0 = nextNode$jscomp$0;
              }
            } else
              "body" === node && releaseSingletonInstance(parentInstance.ownerDocument.body);
          node = nextNode;
        } while (node);
        retryIfBlockedOn(hydrationInstance);
      }
      function hideOrUnhideDehydratedBoundary(suspenseInstance, isHidden) {
        var node = suspenseInstance;
        suspenseInstance = 0;
        do {
          var nextNode = node.nextSibling;
          1 === node.nodeType ? isHidden ? (node._stashedDisplay = node.style.display, node.style.display = "none") : (node.style.display = node._stashedDisplay || "", "" === node.getAttribute("style") && node.removeAttribute("style")) : 3 === node.nodeType && (isHidden ? (node._stashedText = node.nodeValue, node.nodeValue = "") : node.nodeValue = node._stashedText || "");
          if (nextNode && 8 === nextNode.nodeType)
            if (node = nextNode.data, "/$" === node)
              if (0 === suspenseInstance) break;
              else suspenseInstance--;
            else
              "$" !== node && "$?" !== node && "$~" !== node && "$!" !== node || suspenseInstance++;
          node = nextNode;
        } while (node);
      }
      function clearContainerSparingly(container) {
        var nextNode = container.firstChild;
        nextNode && 10 === nextNode.nodeType && (nextNode = nextNode.nextSibling);
        for (; nextNode; ) {
          var node = nextNode;
          nextNode = nextNode.nextSibling;
          switch (node.nodeName) {
            case "HTML":
            case "HEAD":
            case "BODY":
              clearContainerSparingly(node);
              detachDeletedInstance(node);
              continue;
            case "SCRIPT":
            case "STYLE":
              continue;
            case "LINK":
              if ("stylesheet" === node.rel.toLowerCase()) continue;
          }
          container.removeChild(node);
        }
      }
      function canHydrateInstance(instance, type, props, inRootOrSingleton) {
        for (; 1 === instance.nodeType; ) {
          var anyProps = props;
          if (instance.nodeName.toLowerCase() !== type.toLowerCase()) {
            if (!inRootOrSingleton && ("INPUT" !== instance.nodeName || "hidden" !== instance.type))
              break;
          } else if (!inRootOrSingleton)
            if ("input" === type && "hidden" === instance.type) {
              var name = null == anyProps.name ? null : "" + anyProps.name;
              if ("hidden" === anyProps.type && instance.getAttribute("name") === name)
                return instance;
            } else return instance;
          else if (!instance[internalHoistableMarker])
            switch (type) {
              case "meta":
                if (!instance.hasAttribute("itemprop")) break;
                return instance;
              case "link":
                name = instance.getAttribute("rel");
                if ("stylesheet" === name && instance.hasAttribute("data-precedence"))
                  break;
                else if (name !== anyProps.rel || instance.getAttribute("href") !== (null == anyProps.href || "" === anyProps.href ? null : anyProps.href) || instance.getAttribute("crossorigin") !== (null == anyProps.crossOrigin ? null : anyProps.crossOrigin) || instance.getAttribute("title") !== (null == anyProps.title ? null : anyProps.title))
                  break;
                return instance;
              case "style":
                if (instance.hasAttribute("data-precedence")) break;
                return instance;
              case "script":
                name = instance.getAttribute("src");
                if ((name !== (null == anyProps.src ? null : anyProps.src) || instance.getAttribute("type") !== (null == anyProps.type ? null : anyProps.type) || instance.getAttribute("crossorigin") !== (null == anyProps.crossOrigin ? null : anyProps.crossOrigin)) && name && instance.hasAttribute("async") && !instance.hasAttribute("itemprop"))
                  break;
                return instance;
              default:
                return instance;
            }
          instance = getNextHydratable(instance.nextSibling);
          if (null === instance) break;
        }
        return null;
      }
      function canHydrateTextInstance(instance, text, inRootOrSingleton) {
        if ("" === text) return null;
        for (; 3 !== instance.nodeType; ) {
          if ((1 !== instance.nodeType || "INPUT" !== instance.nodeName || "hidden" !== instance.type) && !inRootOrSingleton)
            return null;
          instance = getNextHydratable(instance.nextSibling);
          if (null === instance) return null;
        }
        return instance;
      }
      function canHydrateHydrationBoundary(instance, inRootOrSingleton) {
        for (; 8 !== instance.nodeType; ) {
          if ((1 !== instance.nodeType || "INPUT" !== instance.nodeName || "hidden" !== instance.type) && !inRootOrSingleton)
            return null;
          instance = getNextHydratable(instance.nextSibling);
          if (null === instance) return null;
        }
        return instance;
      }
      function isSuspenseInstancePending(instance) {
        return "$?" === instance.data || "$~" === instance.data;
      }
      function isSuspenseInstanceFallback(instance) {
        return "$!" === instance.data || "$?" === instance.data && "loading" !== instance.ownerDocument.readyState;
      }
      function registerSuspenseInstanceRetry(instance, callback) {
        var ownerDocument = instance.ownerDocument;
        if ("$~" === instance.data) instance._reactRetry = callback;
        else if ("$?" !== instance.data || "loading" !== ownerDocument.readyState)
          callback();
        else {
          var listener = function() {
            callback();
            ownerDocument.removeEventListener("DOMContentLoaded", listener);
          };
          ownerDocument.addEventListener("DOMContentLoaded", listener);
          instance._reactRetry = listener;
        }
      }
      function getNextHydratable(node) {
        for (; null != node; node = node.nextSibling) {
          var nodeType = node.nodeType;
          if (1 === nodeType || 3 === nodeType) break;
          if (8 === nodeType) {
            nodeType = node.data;
            if ("$" === nodeType || "$!" === nodeType || "$?" === nodeType || "$~" === nodeType || "&" === nodeType || "F!" === nodeType || "F" === nodeType)
              break;
            if ("/$" === nodeType || "/&" === nodeType) return null;
          }
        }
        return node;
      }
      var previousHydratableOnEnteringScopedSingleton = null;
      function getNextHydratableInstanceAfterHydrationBoundary(hydrationInstance) {
        hydrationInstance = hydrationInstance.nextSibling;
        for (var depth = 0; hydrationInstance; ) {
          if (8 === hydrationInstance.nodeType) {
            var data = hydrationInstance.data;
            if ("/$" === data || "/&" === data) {
              if (0 === depth)
                return getNextHydratable(hydrationInstance.nextSibling);
              depth--;
            } else
              "$" !== data && "$!" !== data && "$?" !== data && "$~" !== data && "&" !== data || depth++;
          }
          hydrationInstance = hydrationInstance.nextSibling;
        }
        return null;
      }
      function getParentHydrationBoundary(targetInstance) {
        targetInstance = targetInstance.previousSibling;
        for (var depth = 0; targetInstance; ) {
          if (8 === targetInstance.nodeType) {
            var data = targetInstance.data;
            if ("$" === data || "$!" === data || "$?" === data || "$~" === data || "&" === data) {
              if (0 === depth) return targetInstance;
              depth--;
            } else "/$" !== data && "/&" !== data || depth++;
          }
          targetInstance = targetInstance.previousSibling;
        }
        return null;
      }
      function resolveSingletonInstance(type, props, rootContainerInstance) {
        props = getOwnerDocumentFromRootContainer(rootContainerInstance);
        switch (type) {
          case "html":
            type = props.documentElement;
            if (!type) throw Error(formatProdErrorMessage(452));
            return type;
          case "head":
            type = props.head;
            if (!type) throw Error(formatProdErrorMessage(453));
            return type;
          case "body":
            type = props.body;
            if (!type) throw Error(formatProdErrorMessage(454));
            return type;
          default:
            throw Error(formatProdErrorMessage(451));
        }
      }
      function releaseSingletonInstance(instance) {
        for (var attributes = instance.attributes; attributes.length; )
          instance.removeAttributeNode(attributes[0]);
        detachDeletedInstance(instance);
      }
      var preloadPropsMap = /* @__PURE__ */ new Map();
      var preconnectsSet = /* @__PURE__ */ new Set();
      function getHoistableRoot(container) {
        return "function" === typeof container.getRootNode ? container.getRootNode() : 9 === container.nodeType ? container : container.ownerDocument;
      }
      var previousDispatcher = ReactDOMSharedInternals.d;
      ReactDOMSharedInternals.d = {
        f: flushSyncWork,
        r: requestFormReset,
        D: prefetchDNS,
        C: preconnect,
        L: preload,
        m: preloadModule,
        X: preinitScript,
        S: preinitStyle,
        M: preinitModuleScript
      };
      function flushSyncWork() {
        var previousWasRendering = previousDispatcher.f(), wasRendering = flushSyncWork$1();
        return previousWasRendering || wasRendering;
      }
      function requestFormReset(form) {
        var formInst = getInstanceFromNode(form);
        null !== formInst && 5 === formInst.tag && "form" === formInst.type ? requestFormReset$1(formInst) : previousDispatcher.r(form);
      }
      var globalDocument = "undefined" === typeof document ? null : document;
      function preconnectAs(rel, href, crossOrigin) {
        var ownerDocument = globalDocument;
        if (ownerDocument && "string" === typeof href && href) {
          var limitedEscapedHref = escapeSelectorAttributeValueInsideDoubleQuotes(href);
          limitedEscapedHref = 'link[rel="' + rel + '"][href="' + limitedEscapedHref + '"]';
          "string" === typeof crossOrigin && (limitedEscapedHref += '[crossorigin="' + crossOrigin + '"]');
          preconnectsSet.has(limitedEscapedHref) || (preconnectsSet.add(limitedEscapedHref), rel = { rel, crossOrigin, href }, null === ownerDocument.querySelector(limitedEscapedHref) && (href = ownerDocument.createElement("link"), setInitialProperties(href, "link", rel), markNodeAsHoistable(href), ownerDocument.head.appendChild(href)));
        }
      }
      function prefetchDNS(href) {
        previousDispatcher.D(href);
        preconnectAs("dns-prefetch", href, null);
      }
      function preconnect(href, crossOrigin) {
        previousDispatcher.C(href, crossOrigin);
        preconnectAs("preconnect", href, crossOrigin);
      }
      function preload(href, as, options2) {
        previousDispatcher.L(href, as, options2);
        var ownerDocument = globalDocument;
        if (ownerDocument && href && as) {
          var preloadSelector = 'link[rel="preload"][as="' + escapeSelectorAttributeValueInsideDoubleQuotes(as) + '"]';
          "image" === as ? options2 && options2.imageSrcSet ? (preloadSelector += '[imagesrcset="' + escapeSelectorAttributeValueInsideDoubleQuotes(
            options2.imageSrcSet
          ) + '"]', "string" === typeof options2.imageSizes && (preloadSelector += '[imagesizes="' + escapeSelectorAttributeValueInsideDoubleQuotes(
            options2.imageSizes
          ) + '"]')) : preloadSelector += '[href="' + escapeSelectorAttributeValueInsideDoubleQuotes(href) + '"]' : preloadSelector += '[href="' + escapeSelectorAttributeValueInsideDoubleQuotes(href) + '"]';
          var key = preloadSelector;
          switch (as) {
            case "style":
              key = getStyleKey(href);
              break;
            case "script":
              key = getScriptKey(href);
          }
          preloadPropsMap.has(key) || (href = assign(
            {
              rel: "preload",
              href: "image" === as && options2 && options2.imageSrcSet ? void 0 : href,
              as
            },
            options2
          ), preloadPropsMap.set(key, href), null !== ownerDocument.querySelector(preloadSelector) || "style" === as && ownerDocument.querySelector(getStylesheetSelectorFromKey(key)) || "script" === as && ownerDocument.querySelector(getScriptSelectorFromKey(key)) || (as = ownerDocument.createElement("link"), setInitialProperties(as, "link", href), markNodeAsHoistable(as), ownerDocument.head.appendChild(as)));
        }
      }
      function preloadModule(href, options2) {
        previousDispatcher.m(href, options2);
        var ownerDocument = globalDocument;
        if (ownerDocument && href) {
          var as = options2 && "string" === typeof options2.as ? options2.as : "script", preloadSelector = 'link[rel="modulepreload"][as="' + escapeSelectorAttributeValueInsideDoubleQuotes(as) + '"][href="' + escapeSelectorAttributeValueInsideDoubleQuotes(href) + '"]', key = preloadSelector;
          switch (as) {
            case "audioworklet":
            case "paintworklet":
            case "serviceworker":
            case "sharedworker":
            case "worker":
            case "script":
              key = getScriptKey(href);
          }
          if (!preloadPropsMap.has(key) && (href = assign({ rel: "modulepreload", href }, options2), preloadPropsMap.set(key, href), null === ownerDocument.querySelector(preloadSelector))) {
            switch (as) {
              case "audioworklet":
              case "paintworklet":
              case "serviceworker":
              case "sharedworker":
              case "worker":
              case "script":
                if (ownerDocument.querySelector(getScriptSelectorFromKey(key)))
                  return;
            }
            as = ownerDocument.createElement("link");
            setInitialProperties(as, "link", href);
            markNodeAsHoistable(as);
            ownerDocument.head.appendChild(as);
          }
        }
      }
      function preinitStyle(href, precedence, options2) {
        previousDispatcher.S(href, precedence, options2);
        var ownerDocument = globalDocument;
        if (ownerDocument && href) {
          var styles = getResourcesFromRoot(ownerDocument).hoistableStyles, key = getStyleKey(href);
          precedence = precedence || "default";
          var resource = styles.get(key);
          if (!resource) {
            var state = { loading: 0, preload: null };
            if (resource = ownerDocument.querySelector(
              getStylesheetSelectorFromKey(key)
            ))
              state.loading = 5;
            else {
              href = assign(
                { rel: "stylesheet", href, "data-precedence": precedence },
                options2
              );
              (options2 = preloadPropsMap.get(key)) && adoptPreloadPropsForStylesheet(href, options2);
              var link = resource = ownerDocument.createElement("link");
              markNodeAsHoistable(link);
              setInitialProperties(link, "link", href);
              link._p = new Promise(function(resolve, reject) {
                link.onload = resolve;
                link.onerror = reject;
              });
              link.addEventListener("load", function() {
                state.loading |= 1;
              });
              link.addEventListener("error", function() {
                state.loading |= 2;
              });
              state.loading |= 4;
              insertStylesheet(resource, precedence, ownerDocument);
            }
            resource = {
              type: "stylesheet",
              instance: resource,
              count: 1,
              state
            };
            styles.set(key, resource);
          }
        }
      }
      function preinitScript(src, options2) {
        previousDispatcher.X(src, options2);
        var ownerDocument = globalDocument;
        if (ownerDocument && src) {
          var scripts = getResourcesFromRoot(ownerDocument).hoistableScripts, key = getScriptKey(src), resource = scripts.get(key);
          resource || (resource = ownerDocument.querySelector(getScriptSelectorFromKey(key)), resource || (src = assign({ src, async: true }, options2), (options2 = preloadPropsMap.get(key)) && adoptPreloadPropsForScript(src, options2), resource = ownerDocument.createElement("script"), markNodeAsHoistable(resource), setInitialProperties(resource, "link", src), ownerDocument.head.appendChild(resource)), resource = {
            type: "script",
            instance: resource,
            count: 1,
            state: null
          }, scripts.set(key, resource));
        }
      }
      function preinitModuleScript(src, options2) {
        previousDispatcher.M(src, options2);
        var ownerDocument = globalDocument;
        if (ownerDocument && src) {
          var scripts = getResourcesFromRoot(ownerDocument).hoistableScripts, key = getScriptKey(src), resource = scripts.get(key);
          resource || (resource = ownerDocument.querySelector(getScriptSelectorFromKey(key)), resource || (src = assign({ src, async: true, type: "module" }, options2), (options2 = preloadPropsMap.get(key)) && adoptPreloadPropsForScript(src, options2), resource = ownerDocument.createElement("script"), markNodeAsHoistable(resource), setInitialProperties(resource, "link", src), ownerDocument.head.appendChild(resource)), resource = {
            type: "script",
            instance: resource,
            count: 1,
            state: null
          }, scripts.set(key, resource));
        }
      }
      function getResource(type, currentProps, pendingProps, currentResource) {
        var JSCompiler_inline_result = (JSCompiler_inline_result = rootInstanceStackCursor.current) ? getHoistableRoot(JSCompiler_inline_result) : null;
        if (!JSCompiler_inline_result) throw Error(formatProdErrorMessage(446));
        switch (type) {
          case "meta":
          case "title":
            return null;
          case "style":
            return "string" === typeof pendingProps.precedence && "string" === typeof pendingProps.href ? (currentProps = getStyleKey(pendingProps.href), pendingProps = getResourcesFromRoot(
              JSCompiler_inline_result
            ).hoistableStyles, currentResource = pendingProps.get(currentProps), currentResource || (currentResource = {
              type: "style",
              instance: null,
              count: 0,
              state: null
            }, pendingProps.set(currentProps, currentResource)), currentResource) : { type: "void", instance: null, count: 0, state: null };
          case "link":
            if ("stylesheet" === pendingProps.rel && "string" === typeof pendingProps.href && "string" === typeof pendingProps.precedence) {
              type = getStyleKey(pendingProps.href);
              var styles$243 = getResourcesFromRoot(
                JSCompiler_inline_result
              ).hoistableStyles, resource$244 = styles$243.get(type);
              resource$244 || (JSCompiler_inline_result = JSCompiler_inline_result.ownerDocument || JSCompiler_inline_result, resource$244 = {
                type: "stylesheet",
                instance: null,
                count: 0,
                state: { loading: 0, preload: null }
              }, styles$243.set(type, resource$244), (styles$243 = JSCompiler_inline_result.querySelector(
                getStylesheetSelectorFromKey(type)
              )) && !styles$243._p && (resource$244.instance = styles$243, resource$244.state.loading = 5), preloadPropsMap.has(type) || (pendingProps = {
                rel: "preload",
                as: "style",
                href: pendingProps.href,
                crossOrigin: pendingProps.crossOrigin,
                integrity: pendingProps.integrity,
                media: pendingProps.media,
                hrefLang: pendingProps.hrefLang,
                referrerPolicy: pendingProps.referrerPolicy
              }, preloadPropsMap.set(type, pendingProps), styles$243 || preloadStylesheet(
                JSCompiler_inline_result,
                type,
                pendingProps,
                resource$244.state
              )));
              if (currentProps && null === currentResource)
                throw Error(formatProdErrorMessage(528, ""));
              return resource$244;
            }
            if (currentProps && null !== currentResource)
              throw Error(formatProdErrorMessage(529, ""));
            return null;
          case "script":
            return currentProps = pendingProps.async, pendingProps = pendingProps.src, "string" === typeof pendingProps && currentProps && "function" !== typeof currentProps && "symbol" !== typeof currentProps ? (currentProps = getScriptKey(pendingProps), pendingProps = getResourcesFromRoot(
              JSCompiler_inline_result
            ).hoistableScripts, currentResource = pendingProps.get(currentProps), currentResource || (currentResource = {
              type: "script",
              instance: null,
              count: 0,
              state: null
            }, pendingProps.set(currentProps, currentResource)), currentResource) : { type: "void", instance: null, count: 0, state: null };
          default:
            throw Error(formatProdErrorMessage(444, type));
        }
      }
      function getStyleKey(href) {
        return 'href="' + escapeSelectorAttributeValueInsideDoubleQuotes(href) + '"';
      }
      function getStylesheetSelectorFromKey(key) {
        return 'link[rel="stylesheet"][' + key + "]";
      }
      function stylesheetPropsFromRawProps(rawProps) {
        return assign({}, rawProps, {
          "data-precedence": rawProps.precedence,
          precedence: null
        });
      }
      function preloadStylesheet(ownerDocument, key, preloadProps, state) {
        ownerDocument.querySelector('link[rel="preload"][as="style"][' + key + "]") ? state.loading = 1 : (key = ownerDocument.createElement("link"), state.preload = key, key.addEventListener("load", function() {
          return state.loading |= 1;
        }), key.addEventListener("error", function() {
          return state.loading |= 2;
        }), setInitialProperties(key, "link", preloadProps), markNodeAsHoistable(key), ownerDocument.head.appendChild(key));
      }
      function getScriptKey(src) {
        return '[src="' + escapeSelectorAttributeValueInsideDoubleQuotes(src) + '"]';
      }
      function getScriptSelectorFromKey(key) {
        return "script[async]" + key;
      }
      function acquireResource(hoistableRoot, resource, props) {
        resource.count++;
        if (null === resource.instance)
          switch (resource.type) {
            case "style":
              var instance = hoistableRoot.querySelector(
                'style[data-href~="' + escapeSelectorAttributeValueInsideDoubleQuotes(props.href) + '"]'
              );
              if (instance)
                return resource.instance = instance, markNodeAsHoistable(instance), instance;
              var styleProps = assign({}, props, {
                "data-href": props.href,
                "data-precedence": props.precedence,
                href: null,
                precedence: null
              });
              instance = (hoistableRoot.ownerDocument || hoistableRoot).createElement(
                "style"
              );
              markNodeAsHoistable(instance);
              setInitialProperties(instance, "style", styleProps);
              insertStylesheet(instance, props.precedence, hoistableRoot);
              return resource.instance = instance;
            case "stylesheet":
              styleProps = getStyleKey(props.href);
              var instance$249 = hoistableRoot.querySelector(
                getStylesheetSelectorFromKey(styleProps)
              );
              if (instance$249)
                return resource.state.loading |= 4, resource.instance = instance$249, markNodeAsHoistable(instance$249), instance$249;
              instance = stylesheetPropsFromRawProps(props);
              (styleProps = preloadPropsMap.get(styleProps)) && adoptPreloadPropsForStylesheet(instance, styleProps);
              instance$249 = (hoistableRoot.ownerDocument || hoistableRoot).createElement("link");
              markNodeAsHoistable(instance$249);
              var linkInstance = instance$249;
              linkInstance._p = new Promise(function(resolve, reject) {
                linkInstance.onload = resolve;
                linkInstance.onerror = reject;
              });
              setInitialProperties(instance$249, "link", instance);
              resource.state.loading |= 4;
              insertStylesheet(instance$249, props.precedence, hoistableRoot);
              return resource.instance = instance$249;
            case "script":
              instance$249 = getScriptKey(props.src);
              if (styleProps = hoistableRoot.querySelector(
                getScriptSelectorFromKey(instance$249)
              ))
                return resource.instance = styleProps, markNodeAsHoistable(styleProps), styleProps;
              instance = props;
              if (styleProps = preloadPropsMap.get(instance$249))
                instance = assign({}, props), adoptPreloadPropsForScript(instance, styleProps);
              hoistableRoot = hoistableRoot.ownerDocument || hoistableRoot;
              styleProps = hoistableRoot.createElement("script");
              markNodeAsHoistable(styleProps);
              setInitialProperties(styleProps, "link", instance);
              hoistableRoot.head.appendChild(styleProps);
              return resource.instance = styleProps;
            case "void":
              return null;
            default:
              throw Error(formatProdErrorMessage(443, resource.type));
          }
        else
          "stylesheet" === resource.type && 0 === (resource.state.loading & 4) && (instance = resource.instance, resource.state.loading |= 4, insertStylesheet(instance, props.precedence, hoistableRoot));
        return resource.instance;
      }
      function insertStylesheet(instance, precedence, root2) {
        for (var nodes = root2.querySelectorAll(
          'link[rel="stylesheet"][data-precedence],style[data-precedence]'
        ), last = nodes.length ? nodes[nodes.length - 1] : null, prior = last, i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          if (node.dataset.precedence === precedence) prior = node;
          else if (prior !== last) break;
        }
        prior ? prior.parentNode.insertBefore(instance, prior.nextSibling) : (precedence = 9 === root2.nodeType ? root2.head : root2, precedence.insertBefore(instance, precedence.firstChild));
      }
      function adoptPreloadPropsForStylesheet(stylesheetProps, preloadProps) {
        null == stylesheetProps.crossOrigin && (stylesheetProps.crossOrigin = preloadProps.crossOrigin);
        null == stylesheetProps.referrerPolicy && (stylesheetProps.referrerPolicy = preloadProps.referrerPolicy);
        null == stylesheetProps.title && (stylesheetProps.title = preloadProps.title);
      }
      function adoptPreloadPropsForScript(scriptProps, preloadProps) {
        null == scriptProps.crossOrigin && (scriptProps.crossOrigin = preloadProps.crossOrigin);
        null == scriptProps.referrerPolicy && (scriptProps.referrerPolicy = preloadProps.referrerPolicy);
        null == scriptProps.integrity && (scriptProps.integrity = preloadProps.integrity);
      }
      var tagCaches = null;
      function getHydratableHoistableCache(type, keyAttribute, ownerDocument) {
        if (null === tagCaches) {
          var cache2 = /* @__PURE__ */ new Map();
          var caches = tagCaches = /* @__PURE__ */ new Map();
          caches.set(ownerDocument, cache2);
        } else
          caches = tagCaches, cache2 = caches.get(ownerDocument), cache2 || (cache2 = /* @__PURE__ */ new Map(), caches.set(ownerDocument, cache2));
        if (cache2.has(type)) return cache2;
        cache2.set(type, null);
        ownerDocument = ownerDocument.getElementsByTagName(type);
        for (caches = 0; caches < ownerDocument.length; caches++) {
          var node = ownerDocument[caches];
          if (!(node[internalHoistableMarker] || node[internalInstanceKey] || "link" === type && "stylesheet" === node.getAttribute("rel")) && "http://www.w3.org/2000/svg" !== node.namespaceURI) {
            var nodeKey = node.getAttribute(keyAttribute) || "";
            nodeKey = type + nodeKey;
            var existing = cache2.get(nodeKey);
            existing ? existing.push(node) : cache2.set(nodeKey, [node]);
          }
        }
        return cache2;
      }
      function mountHoistable(hoistableRoot, type, instance) {
        hoistableRoot = hoistableRoot.ownerDocument || hoistableRoot;
        hoistableRoot.head.insertBefore(
          instance,
          "title" === type ? hoistableRoot.querySelector("head > title") : null
        );
      }
      function isHostHoistableType(type, props, hostContext) {
        if (1 === hostContext || null != props.itemProp) return false;
        switch (type) {
          case "meta":
          case "title":
            return true;
          case "style":
            if ("string" !== typeof props.precedence || "string" !== typeof props.href || "" === props.href)
              break;
            return true;
          case "link":
            if ("string" !== typeof props.rel || "string" !== typeof props.href || "" === props.href || props.onLoad || props.onError)
              break;
            switch (props.rel) {
              case "stylesheet":
                return type = props.disabled, "string" === typeof props.precedence && null == type;
              default:
                return true;
            }
          case "script":
            if (props.async && "function" !== typeof props.async && "symbol" !== typeof props.async && !props.onLoad && !props.onError && props.src && "string" === typeof props.src)
              return true;
        }
        return false;
      }
      function preloadResource(resource) {
        return "stylesheet" === resource.type && 0 === (resource.state.loading & 3) ? false : true;
      }
      function suspendResource(state, hoistableRoot, resource, props) {
        if ("stylesheet" === resource.type && ("string" !== typeof props.media || false !== matchMedia(props.media).matches) && 0 === (resource.state.loading & 4)) {
          if (null === resource.instance) {
            var key = getStyleKey(props.href), instance = hoistableRoot.querySelector(
              getStylesheetSelectorFromKey(key)
            );
            if (instance) {
              hoistableRoot = instance._p;
              null !== hoistableRoot && "object" === typeof hoistableRoot && "function" === typeof hoistableRoot.then && (state.count++, state = onUnsuspend.bind(state), hoistableRoot.then(state, state));
              resource.state.loading |= 4;
              resource.instance = instance;
              markNodeAsHoistable(instance);
              return;
            }
            instance = hoistableRoot.ownerDocument || hoistableRoot;
            props = stylesheetPropsFromRawProps(props);
            (key = preloadPropsMap.get(key)) && adoptPreloadPropsForStylesheet(props, key);
            instance = instance.createElement("link");
            markNodeAsHoistable(instance);
            var linkInstance = instance;
            linkInstance._p = new Promise(function(resolve, reject) {
              linkInstance.onload = resolve;
              linkInstance.onerror = reject;
            });
            setInitialProperties(instance, "link", props);
            resource.instance = instance;
          }
          null === state.stylesheets && (state.stylesheets = /* @__PURE__ */ new Map());
          state.stylesheets.set(resource, hoistableRoot);
          (hoistableRoot = resource.state.preload) && 0 === (resource.state.loading & 3) && (state.count++, resource = onUnsuspend.bind(state), hoistableRoot.addEventListener("load", resource), hoistableRoot.addEventListener("error", resource));
        }
      }
      var estimatedBytesWithinLimit = 0;
      function waitForCommitToBeReady(state, timeoutOffset) {
        state.stylesheets && 0 === state.count && insertSuspendedStylesheets(state, state.stylesheets);
        return 0 < state.count || 0 < state.imgCount ? function(commit) {
          var stylesheetTimer = setTimeout(function() {
            state.stylesheets && insertSuspendedStylesheets(state, state.stylesheets);
            if (state.unsuspend) {
              var unsuspend = state.unsuspend;
              state.unsuspend = null;
              unsuspend();
            }
          }, 6e4 + timeoutOffset);
          0 < state.imgBytes && 0 === estimatedBytesWithinLimit && (estimatedBytesWithinLimit = 62500 * estimateBandwidth());
          var imgTimer = setTimeout(
            function() {
              state.waitingForImages = false;
              if (0 === state.count && (state.stylesheets && insertSuspendedStylesheets(state, state.stylesheets), state.unsuspend)) {
                var unsuspend = state.unsuspend;
                state.unsuspend = null;
                unsuspend();
              }
            },
            (state.imgBytes > estimatedBytesWithinLimit ? 50 : 800) + timeoutOffset
          );
          state.unsuspend = commit;
          return function() {
            state.unsuspend = null;
            clearTimeout(stylesheetTimer);
            clearTimeout(imgTimer);
          };
        } : null;
      }
      function onUnsuspend() {
        this.count--;
        if (0 === this.count && (0 === this.imgCount || !this.waitingForImages)) {
          if (this.stylesheets) insertSuspendedStylesheets(this, this.stylesheets);
          else if (this.unsuspend) {
            var unsuspend = this.unsuspend;
            this.unsuspend = null;
            unsuspend();
          }
        }
      }
      var precedencesByRoot = null;
      function insertSuspendedStylesheets(state, resources) {
        state.stylesheets = null;
        null !== state.unsuspend && (state.count++, precedencesByRoot = /* @__PURE__ */ new Map(), resources.forEach(insertStylesheetIntoRoot, state), precedencesByRoot = null, onUnsuspend.call(state));
      }
      function insertStylesheetIntoRoot(root2, resource) {
        if (!(resource.state.loading & 4)) {
          var precedences = precedencesByRoot.get(root2);
          if (precedences) var last = precedences.get(null);
          else {
            precedences = /* @__PURE__ */ new Map();
            precedencesByRoot.set(root2, precedences);
            for (var nodes = root2.querySelectorAll(
              "link[data-precedence],style[data-precedence]"
            ), i = 0; i < nodes.length; i++) {
              var node = nodes[i];
              if ("LINK" === node.nodeName || "not all" !== node.getAttribute("media"))
                precedences.set(node.dataset.precedence, node), last = node;
            }
            last && precedences.set(null, last);
          }
          nodes = resource.instance;
          node = nodes.getAttribute("data-precedence");
          i = precedences.get(node) || last;
          i === last && precedences.set(null, nodes);
          precedences.set(node, nodes);
          this.count++;
          last = onUnsuspend.bind(this);
          nodes.addEventListener("load", last);
          nodes.addEventListener("error", last);
          i ? i.parentNode.insertBefore(nodes, i.nextSibling) : (root2 = 9 === root2.nodeType ? root2.head : root2, root2.insertBefore(nodes, root2.firstChild));
          resource.state.loading |= 4;
        }
      }
      var HostTransitionContext = {
        $$typeof: REACT_CONTEXT_TYPE,
        Provider: null,
        Consumer: null,
        _currentValue: sharedNotPendingObject,
        _currentValue2: sharedNotPendingObject,
        _threadCount: 0
      };
      function FiberRootNode(containerInfo, tag, hydrate, identifierPrefix, onUncaughtError, onCaughtError, onRecoverableError, onDefaultTransitionIndicator, formState) {
        this.tag = 1;
        this.containerInfo = containerInfo;
        this.pingCache = this.current = this.pendingChildren = null;
        this.timeoutHandle = -1;
        this.callbackNode = this.next = this.pendingContext = this.context = this.cancelPendingCommit = null;
        this.callbackPriority = 0;
        this.expirationTimes = createLaneMap(-1);
        this.entangledLanes = this.shellSuspendCounter = this.errorRecoveryDisabledLanes = this.expiredLanes = this.warmLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0;
        this.entanglements = createLaneMap(0);
        this.hiddenUpdates = createLaneMap(null);
        this.identifierPrefix = identifierPrefix;
        this.onUncaughtError = onUncaughtError;
        this.onCaughtError = onCaughtError;
        this.onRecoverableError = onRecoverableError;
        this.pooledCache = null;
        this.pooledCacheLanes = 0;
        this.formState = formState;
        this.incompleteTransitions = /* @__PURE__ */ new Map();
      }
      function createFiberRoot(containerInfo, tag, hydrate, initialChildren, hydrationCallbacks, isStrictMode, identifierPrefix, formState, onUncaughtError, onCaughtError, onRecoverableError, onDefaultTransitionIndicator) {
        containerInfo = new FiberRootNode(
          containerInfo,
          tag,
          hydrate,
          identifierPrefix,
          onUncaughtError,
          onCaughtError,
          onRecoverableError,
          onDefaultTransitionIndicator,
          formState
        );
        tag = 1;
        true === isStrictMode && (tag |= 24);
        isStrictMode = createFiberImplClass(3, null, null, tag);
        containerInfo.current = isStrictMode;
        isStrictMode.stateNode = containerInfo;
        tag = createCache();
        tag.refCount++;
        containerInfo.pooledCache = tag;
        tag.refCount++;
        isStrictMode.memoizedState = {
          element: initialChildren,
          isDehydrated: hydrate,
          cache: tag
        };
        initializeUpdateQueue(isStrictMode);
        return containerInfo;
      }
      function getContextForSubtree(parentComponent) {
        if (!parentComponent) return emptyContextObject;
        parentComponent = emptyContextObject;
        return parentComponent;
      }
      function updateContainerImpl(rootFiber, lane, element, container, parentComponent, callback) {
        parentComponent = getContextForSubtree(parentComponent);
        null === container.context ? container.context = parentComponent : container.pendingContext = parentComponent;
        container = createUpdate(lane);
        container.payload = { element };
        callback = void 0 === callback ? null : callback;
        null !== callback && (container.callback = callback);
        element = enqueueUpdate(rootFiber, container, lane);
        null !== element && (scheduleUpdateOnFiber(element, rootFiber, lane), entangleTransitions(element, rootFiber, lane));
      }
      function markRetryLaneImpl(fiber, retryLane) {
        fiber = fiber.memoizedState;
        if (null !== fiber && null !== fiber.dehydrated) {
          var a = fiber.retryLane;
          fiber.retryLane = 0 !== a && a < retryLane ? a : retryLane;
        }
      }
      function markRetryLaneIfNotHydrated(fiber, retryLane) {
        markRetryLaneImpl(fiber, retryLane);
        (fiber = fiber.alternate) && markRetryLaneImpl(fiber, retryLane);
      }
      function attemptContinuousHydration(fiber) {
        if (13 === fiber.tag || 31 === fiber.tag) {
          var root2 = enqueueConcurrentRenderForLane(fiber, 67108864);
          null !== root2 && scheduleUpdateOnFiber(root2, fiber, 67108864);
          markRetryLaneIfNotHydrated(fiber, 67108864);
        }
      }
      function attemptHydrationAtCurrentPriority(fiber) {
        if (13 === fiber.tag || 31 === fiber.tag) {
          var lane = requestUpdateLane();
          lane = getBumpedLaneForHydrationByLane(lane);
          var root2 = enqueueConcurrentRenderForLane(fiber, lane);
          null !== root2 && scheduleUpdateOnFiber(root2, fiber, lane);
          markRetryLaneIfNotHydrated(fiber, lane);
        }
      }
      var _enabled = true;
      function dispatchDiscreteEvent(domEventName, eventSystemFlags, container, nativeEvent) {
        var prevTransition = ReactSharedInternals.T;
        ReactSharedInternals.T = null;
        var previousPriority = ReactDOMSharedInternals.p;
        try {
          ReactDOMSharedInternals.p = 2, dispatchEvent(domEventName, eventSystemFlags, container, nativeEvent);
        } finally {
          ReactDOMSharedInternals.p = previousPriority, ReactSharedInternals.T = prevTransition;
        }
      }
      function dispatchContinuousEvent(domEventName, eventSystemFlags, container, nativeEvent) {
        var prevTransition = ReactSharedInternals.T;
        ReactSharedInternals.T = null;
        var previousPriority = ReactDOMSharedInternals.p;
        try {
          ReactDOMSharedInternals.p = 8, dispatchEvent(domEventName, eventSystemFlags, container, nativeEvent);
        } finally {
          ReactDOMSharedInternals.p = previousPriority, ReactSharedInternals.T = prevTransition;
        }
      }
      function dispatchEvent(domEventName, eventSystemFlags, targetContainer, nativeEvent) {
        if (_enabled) {
          var blockedOn = findInstanceBlockingEvent(nativeEvent);
          if (null === blockedOn)
            dispatchEventForPluginEventSystem(
              domEventName,
              eventSystemFlags,
              nativeEvent,
              return_targetInst,
              targetContainer
            ), clearIfContinuousEvent(domEventName, nativeEvent);
          else if (queueIfContinuousEvent(
            blockedOn,
            domEventName,
            eventSystemFlags,
            targetContainer,
            nativeEvent
          ))
            nativeEvent.stopPropagation();
          else if (clearIfContinuousEvent(domEventName, nativeEvent), eventSystemFlags & 4 && -1 < discreteReplayableEvents.indexOf(domEventName)) {
            for (; null !== blockedOn; ) {
              var fiber = getInstanceFromNode(blockedOn);
              if (null !== fiber)
                switch (fiber.tag) {
                  case 3:
                    fiber = fiber.stateNode;
                    if (fiber.current.memoizedState.isDehydrated) {
                      var lanes = getHighestPriorityLanes(fiber.pendingLanes);
                      if (0 !== lanes) {
                        var root2 = fiber;
                        root2.pendingLanes |= 2;
                        for (root2.entangledLanes |= 2; lanes; ) {
                          var lane = 1 << 31 - clz32(lanes);
                          root2.entanglements[1] |= lane;
                          lanes &= ~lane;
                        }
                        ensureRootIsScheduled(fiber);
                        0 === (executionContext & 6) && (workInProgressRootRenderTargetTime = now() + 500, flushSyncWorkAcrossRoots_impl(0, false));
                      }
                    }
                    break;
                  case 31:
                  case 13:
                    root2 = enqueueConcurrentRenderForLane(fiber, 2), null !== root2 && scheduleUpdateOnFiber(root2, fiber, 2), flushSyncWork$1(), markRetryLaneIfNotHydrated(fiber, 2);
                }
              fiber = findInstanceBlockingEvent(nativeEvent);
              null === fiber && dispatchEventForPluginEventSystem(
                domEventName,
                eventSystemFlags,
                nativeEvent,
                return_targetInst,
                targetContainer
              );
              if (fiber === blockedOn) break;
              blockedOn = fiber;
            }
            null !== blockedOn && nativeEvent.stopPropagation();
          } else
            dispatchEventForPluginEventSystem(
              domEventName,
              eventSystemFlags,
              nativeEvent,
              null,
              targetContainer
            );
        }
      }
      function findInstanceBlockingEvent(nativeEvent) {
        nativeEvent = getEventTarget(nativeEvent);
        return findInstanceBlockingTarget(nativeEvent);
      }
      var return_targetInst = null;
      function findInstanceBlockingTarget(targetNode) {
        return_targetInst = null;
        targetNode = getClosestInstanceFromNode(targetNode);
        if (null !== targetNode) {
          var nearestMounted = getNearestMountedFiber(targetNode);
          if (null === nearestMounted) targetNode = null;
          else {
            var tag = nearestMounted.tag;
            if (13 === tag) {
              targetNode = getSuspenseInstanceFromFiber(nearestMounted);
              if (null !== targetNode) return targetNode;
              targetNode = null;
            } else if (31 === tag) {
              targetNode = getActivityInstanceFromFiber(nearestMounted);
              if (null !== targetNode) return targetNode;
              targetNode = null;
            } else if (3 === tag) {
              if (nearestMounted.stateNode.current.memoizedState.isDehydrated)
                return 3 === nearestMounted.tag ? nearestMounted.stateNode.containerInfo : null;
              targetNode = null;
            } else nearestMounted !== targetNode && (targetNode = null);
          }
        }
        return_targetInst = targetNode;
        return null;
      }
      function getEventPriority(domEventName) {
        switch (domEventName) {
          case "beforetoggle":
          case "cancel":
          case "click":
          case "close":
          case "contextmenu":
          case "copy":
          case "cut":
          case "auxclick":
          case "dblclick":
          case "dragend":
          case "dragstart":
          case "drop":
          case "focusin":
          case "focusout":
          case "input":
          case "invalid":
          case "keydown":
          case "keypress":
          case "keyup":
          case "mousedown":
          case "mouseup":
          case "paste":
          case "pause":
          case "play":
          case "pointercancel":
          case "pointerdown":
          case "pointerup":
          case "ratechange":
          case "reset":
          case "resize":
          case "seeked":
          case "submit":
          case "toggle":
          case "touchcancel":
          case "touchend":
          case "touchstart":
          case "volumechange":
          case "change":
          case "selectionchange":
          case "textInput":
          case "compositionstart":
          case "compositionend":
          case "compositionupdate":
          case "beforeblur":
          case "afterblur":
          case "beforeinput":
          case "blur":
          case "fullscreenchange":
          case "focus":
          case "hashchange":
          case "popstate":
          case "select":
          case "selectstart":
            return 2;
          case "drag":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "mousemove":
          case "mouseout":
          case "mouseover":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "scroll":
          case "touchmove":
          case "wheel":
          case "mouseenter":
          case "mouseleave":
          case "pointerenter":
          case "pointerleave":
            return 8;
          case "message":
            switch (getCurrentPriorityLevel()) {
              case ImmediatePriority:
                return 2;
              case UserBlockingPriority:
                return 8;
              case NormalPriority$1:
              case LowPriority:
                return 32;
              case IdlePriority:
                return 268435456;
              default:
                return 32;
            }
          default:
            return 32;
        }
      }
      var hasScheduledReplayAttempt = false;
      var queuedFocus = null;
      var queuedDrag = null;
      var queuedMouse = null;
      var queuedPointers = /* @__PURE__ */ new Map();
      var queuedPointerCaptures = /* @__PURE__ */ new Map();
      var queuedExplicitHydrationTargets = [];
      var discreteReplayableEvents = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset".split(
        " "
      );
      function clearIfContinuousEvent(domEventName, nativeEvent) {
        switch (domEventName) {
          case "focusin":
          case "focusout":
            queuedFocus = null;
            break;
          case "dragenter":
          case "dragleave":
            queuedDrag = null;
            break;
          case "mouseover":
          case "mouseout":
            queuedMouse = null;
            break;
          case "pointerover":
          case "pointerout":
            queuedPointers.delete(nativeEvent.pointerId);
            break;
          case "gotpointercapture":
          case "lostpointercapture":
            queuedPointerCaptures.delete(nativeEvent.pointerId);
        }
      }
      function accumulateOrCreateContinuousQueuedReplayableEvent(existingQueuedEvent, blockedOn, domEventName, eventSystemFlags, targetContainer, nativeEvent) {
        if (null === existingQueuedEvent || existingQueuedEvent.nativeEvent !== nativeEvent)
          return existingQueuedEvent = {
            blockedOn,
            domEventName,
            eventSystemFlags,
            nativeEvent,
            targetContainers: [targetContainer]
          }, null !== blockedOn && (blockedOn = getInstanceFromNode(blockedOn), null !== blockedOn && attemptContinuousHydration(blockedOn)), existingQueuedEvent;
        existingQueuedEvent.eventSystemFlags |= eventSystemFlags;
        blockedOn = existingQueuedEvent.targetContainers;
        null !== targetContainer && -1 === blockedOn.indexOf(targetContainer) && blockedOn.push(targetContainer);
        return existingQueuedEvent;
      }
      function queueIfContinuousEvent(blockedOn, domEventName, eventSystemFlags, targetContainer, nativeEvent) {
        switch (domEventName) {
          case "focusin":
            return queuedFocus = accumulateOrCreateContinuousQueuedReplayableEvent(
              queuedFocus,
              blockedOn,
              domEventName,
              eventSystemFlags,
              targetContainer,
              nativeEvent
            ), true;
          case "dragenter":
            return queuedDrag = accumulateOrCreateContinuousQueuedReplayableEvent(
              queuedDrag,
              blockedOn,
              domEventName,
              eventSystemFlags,
              targetContainer,
              nativeEvent
            ), true;
          case "mouseover":
            return queuedMouse = accumulateOrCreateContinuousQueuedReplayableEvent(
              queuedMouse,
              blockedOn,
              domEventName,
              eventSystemFlags,
              targetContainer,
              nativeEvent
            ), true;
          case "pointerover":
            var pointerId = nativeEvent.pointerId;
            queuedPointers.set(
              pointerId,
              accumulateOrCreateContinuousQueuedReplayableEvent(
                queuedPointers.get(pointerId) || null,
                blockedOn,
                domEventName,
                eventSystemFlags,
                targetContainer,
                nativeEvent
              )
            );
            return true;
          case "gotpointercapture":
            return pointerId = nativeEvent.pointerId, queuedPointerCaptures.set(
              pointerId,
              accumulateOrCreateContinuousQueuedReplayableEvent(
                queuedPointerCaptures.get(pointerId) || null,
                blockedOn,
                domEventName,
                eventSystemFlags,
                targetContainer,
                nativeEvent
              )
            ), true;
        }
        return false;
      }
      function attemptExplicitHydrationTarget(queuedTarget) {
        var targetInst = getClosestInstanceFromNode(queuedTarget.target);
        if (null !== targetInst) {
          var nearestMounted = getNearestMountedFiber(targetInst);
          if (null !== nearestMounted) {
            if (targetInst = nearestMounted.tag, 13 === targetInst) {
              if (targetInst = getSuspenseInstanceFromFiber(nearestMounted), null !== targetInst) {
                queuedTarget.blockedOn = targetInst;
                runWithPriority(queuedTarget.priority, function() {
                  attemptHydrationAtCurrentPriority(nearestMounted);
                });
                return;
              }
            } else if (31 === targetInst) {
              if (targetInst = getActivityInstanceFromFiber(nearestMounted), null !== targetInst) {
                queuedTarget.blockedOn = targetInst;
                runWithPriority(queuedTarget.priority, function() {
                  attemptHydrationAtCurrentPriority(nearestMounted);
                });
                return;
              }
            } else if (3 === targetInst && nearestMounted.stateNode.current.memoizedState.isDehydrated) {
              queuedTarget.blockedOn = 3 === nearestMounted.tag ? nearestMounted.stateNode.containerInfo : null;
              return;
            }
          }
        }
        queuedTarget.blockedOn = null;
      }
      function attemptReplayContinuousQueuedEvent(queuedEvent) {
        if (null !== queuedEvent.blockedOn) return false;
        for (var targetContainers = queuedEvent.targetContainers; 0 < targetContainers.length; ) {
          var nextBlockedOn = findInstanceBlockingEvent(queuedEvent.nativeEvent);
          if (null === nextBlockedOn) {
            nextBlockedOn = queuedEvent.nativeEvent;
            var nativeEventClone = new nextBlockedOn.constructor(
              nextBlockedOn.type,
              nextBlockedOn
            );
            currentReplayingEvent = nativeEventClone;
            nextBlockedOn.target.dispatchEvent(nativeEventClone);
            currentReplayingEvent = null;
          } else
            return targetContainers = getInstanceFromNode(nextBlockedOn), null !== targetContainers && attemptContinuousHydration(targetContainers), queuedEvent.blockedOn = nextBlockedOn, false;
          targetContainers.shift();
        }
        return true;
      }
      function attemptReplayContinuousQueuedEventInMap(queuedEvent, key, map) {
        attemptReplayContinuousQueuedEvent(queuedEvent) && map.delete(key);
      }
      function replayUnblockedEvents() {
        hasScheduledReplayAttempt = false;
        null !== queuedFocus && attemptReplayContinuousQueuedEvent(queuedFocus) && (queuedFocus = null);
        null !== queuedDrag && attemptReplayContinuousQueuedEvent(queuedDrag) && (queuedDrag = null);
        null !== queuedMouse && attemptReplayContinuousQueuedEvent(queuedMouse) && (queuedMouse = null);
        queuedPointers.forEach(attemptReplayContinuousQueuedEventInMap);
        queuedPointerCaptures.forEach(attemptReplayContinuousQueuedEventInMap);
      }
      function scheduleCallbackIfUnblocked(queuedEvent, unblocked) {
        queuedEvent.blockedOn === unblocked && (queuedEvent.blockedOn = null, hasScheduledReplayAttempt || (hasScheduledReplayAttempt = true, Scheduler.unstable_scheduleCallback(
          Scheduler.unstable_NormalPriority,
          replayUnblockedEvents
        )));
      }
      var lastScheduledReplayQueue = null;
      function scheduleReplayQueueIfNeeded(formReplayingQueue) {
        lastScheduledReplayQueue !== formReplayingQueue && (lastScheduledReplayQueue = formReplayingQueue, Scheduler.unstable_scheduleCallback(
          Scheduler.unstable_NormalPriority,
          function() {
            lastScheduledReplayQueue === formReplayingQueue && (lastScheduledReplayQueue = null);
            for (var i = 0; i < formReplayingQueue.length; i += 3) {
              var form = formReplayingQueue[i], submitterOrAction = formReplayingQueue[i + 1], formData = formReplayingQueue[i + 2];
              if ("function" !== typeof submitterOrAction)
                if (null === findInstanceBlockingTarget(submitterOrAction || form))
                  continue;
                else break;
              var formInst = getInstanceFromNode(form);
              null !== formInst && (formReplayingQueue.splice(i, 3), i -= 3, startHostTransition(
                formInst,
                {
                  pending: true,
                  data: formData,
                  method: form.method,
                  action: submitterOrAction
                },
                submitterOrAction,
                formData
              ));
            }
          }
        ));
      }
      function retryIfBlockedOn(unblocked) {
        function unblock(queuedEvent) {
          return scheduleCallbackIfUnblocked(queuedEvent, unblocked);
        }
        null !== queuedFocus && scheduleCallbackIfUnblocked(queuedFocus, unblocked);
        null !== queuedDrag && scheduleCallbackIfUnblocked(queuedDrag, unblocked);
        null !== queuedMouse && scheduleCallbackIfUnblocked(queuedMouse, unblocked);
        queuedPointers.forEach(unblock);
        queuedPointerCaptures.forEach(unblock);
        for (var i = 0; i < queuedExplicitHydrationTargets.length; i++) {
          var queuedTarget = queuedExplicitHydrationTargets[i];
          queuedTarget.blockedOn === unblocked && (queuedTarget.blockedOn = null);
        }
        for (; 0 < queuedExplicitHydrationTargets.length && (i = queuedExplicitHydrationTargets[0], null === i.blockedOn); )
          attemptExplicitHydrationTarget(i), null === i.blockedOn && queuedExplicitHydrationTargets.shift();
        i = (unblocked.ownerDocument || unblocked).$$reactFormReplay;
        if (null != i)
          for (queuedTarget = 0; queuedTarget < i.length; queuedTarget += 3) {
            var form = i[queuedTarget], submitterOrAction = i[queuedTarget + 1], formProps = form[internalPropsKey] || null;
            if ("function" === typeof submitterOrAction)
              formProps || scheduleReplayQueueIfNeeded(i);
            else if (formProps) {
              var action = null;
              if (submitterOrAction && submitterOrAction.hasAttribute("formAction"))
                if (form = submitterOrAction, formProps = submitterOrAction[internalPropsKey] || null)
                  action = formProps.formAction;
                else {
                  if (null !== findInstanceBlockingTarget(form)) continue;
                }
              else action = formProps.action;
              "function" === typeof action ? i[queuedTarget + 1] = action : (i.splice(queuedTarget, 3), queuedTarget -= 3);
              scheduleReplayQueueIfNeeded(i);
            }
          }
      }
      function defaultOnDefaultTransitionIndicator() {
        function handleNavigate(event) {
          event.canIntercept && "react-transition" === event.info && event.intercept({
            handler: function() {
              return new Promise(function(resolve) {
                return pendingResolve = resolve;
              });
            },
            focusReset: "manual",
            scroll: "manual"
          });
        }
        function handleNavigateComplete() {
          null !== pendingResolve && (pendingResolve(), pendingResolve = null);
          isCancelled || setTimeout(startFakeNavigation, 20);
        }
        function startFakeNavigation() {
          if (!isCancelled && !navigation.transition) {
            var currentEntry = navigation.currentEntry;
            currentEntry && null != currentEntry.url && navigation.navigate(currentEntry.url, {
              state: currentEntry.getState(),
              info: "react-transition",
              history: "replace"
            });
          }
        }
        if ("object" === typeof navigation) {
          var isCancelled = false, pendingResolve = null;
          navigation.addEventListener("navigate", handleNavigate);
          navigation.addEventListener("navigatesuccess", handleNavigateComplete);
          navigation.addEventListener("navigateerror", handleNavigateComplete);
          setTimeout(startFakeNavigation, 100);
          return function() {
            isCancelled = true;
            navigation.removeEventListener("navigate", handleNavigate);
            navigation.removeEventListener("navigatesuccess", handleNavigateComplete);
            navigation.removeEventListener("navigateerror", handleNavigateComplete);
            null !== pendingResolve && (pendingResolve(), pendingResolve = null);
          };
        }
      }
      function ReactDOMRoot(internalRoot) {
        this._internalRoot = internalRoot;
      }
      ReactDOMHydrationRoot.prototype.render = ReactDOMRoot.prototype.render = function(children) {
        var root2 = this._internalRoot;
        if (null === root2) throw Error(formatProdErrorMessage(409));
        var current = root2.current, lane = requestUpdateLane();
        updateContainerImpl(current, lane, children, root2, null, null);
      };
      ReactDOMHydrationRoot.prototype.unmount = ReactDOMRoot.prototype.unmount = function() {
        var root2 = this._internalRoot;
        if (null !== root2) {
          this._internalRoot = null;
          var container = root2.containerInfo;
          updateContainerImpl(root2.current, 2, null, root2, null, null);
          flushSyncWork$1();
          container[internalContainerInstanceKey] = null;
        }
      };
      function ReactDOMHydrationRoot(internalRoot) {
        this._internalRoot = internalRoot;
      }
      ReactDOMHydrationRoot.prototype.unstable_scheduleHydration = function(target) {
        if (target) {
          var updatePriority = resolveUpdatePriority();
          target = { blockedOn: null, target, priority: updatePriority };
          for (var i = 0; i < queuedExplicitHydrationTargets.length && 0 !== updatePriority && updatePriority < queuedExplicitHydrationTargets[i].priority; i++) ;
          queuedExplicitHydrationTargets.splice(i, 0, target);
          0 === i && attemptExplicitHydrationTarget(target);
        }
      };
      var isomorphicReactPackageVersion$jscomp$inline_1840 = React.version;
      if ("19.2.7" !== isomorphicReactPackageVersion$jscomp$inline_1840)
        throw Error(
          formatProdErrorMessage(
            527,
            isomorphicReactPackageVersion$jscomp$inline_1840,
            "19.2.7"
          )
        );
      ReactDOMSharedInternals.findDOMNode = function(componentOrElement) {
        var fiber = componentOrElement._reactInternals;
        if (void 0 === fiber) {
          if ("function" === typeof componentOrElement.render)
            throw Error(formatProdErrorMessage(188));
          componentOrElement = Object.keys(componentOrElement).join(",");
          throw Error(formatProdErrorMessage(268, componentOrElement));
        }
        componentOrElement = findCurrentFiberUsingSlowPath(fiber);
        componentOrElement = null !== componentOrElement ? findCurrentHostFiberImpl(componentOrElement) : null;
        componentOrElement = null === componentOrElement ? null : componentOrElement.stateNode;
        return componentOrElement;
      };
      var internals$jscomp$inline_2347 = {
        bundleType: 0,
        version: "19.2.7",
        rendererPackageName: "react-dom",
        currentDispatcherRef: ReactSharedInternals,
        reconcilerVersion: "19.2.7"
      };
      if ("undefined" !== typeof __REACT_DEVTOOLS_GLOBAL_HOOK__) {
        hook$jscomp$inline_2348 = __REACT_DEVTOOLS_GLOBAL_HOOK__;
        if (!hook$jscomp$inline_2348.isDisabled && hook$jscomp$inline_2348.supportsFiber)
          try {
            rendererID = hook$jscomp$inline_2348.inject(
              internals$jscomp$inline_2347
            ), injectedHook = hook$jscomp$inline_2348;
          } catch (err) {
          }
      }
      var hook$jscomp$inline_2348;
      exports.createRoot = function(container, options2) {
        if (!isValidContainer(container)) throw Error(formatProdErrorMessage(299));
        var isStrictMode = false, identifierPrefix = "", onUncaughtError = defaultOnUncaughtError, onCaughtError = defaultOnCaughtError, onRecoverableError = defaultOnRecoverableError;
        null !== options2 && void 0 !== options2 && (true === options2.unstable_strictMode && (isStrictMode = true), void 0 !== options2.identifierPrefix && (identifierPrefix = options2.identifierPrefix), void 0 !== options2.onUncaughtError && (onUncaughtError = options2.onUncaughtError), void 0 !== options2.onCaughtError && (onCaughtError = options2.onCaughtError), void 0 !== options2.onRecoverableError && (onRecoverableError = options2.onRecoverableError));
        options2 = createFiberRoot(
          container,
          1,
          false,
          null,
          null,
          isStrictMode,
          identifierPrefix,
          null,
          onUncaughtError,
          onCaughtError,
          onRecoverableError,
          defaultOnDefaultTransitionIndicator
        );
        container[internalContainerInstanceKey] = options2.current;
        listenToAllSupportedEvents(container);
        return new ReactDOMRoot(options2);
      };
      exports.hydrateRoot = function(container, initialChildren, options2) {
        if (!isValidContainer(container)) throw Error(formatProdErrorMessage(299));
        var isStrictMode = false, identifierPrefix = "", onUncaughtError = defaultOnUncaughtError, onCaughtError = defaultOnCaughtError, onRecoverableError = defaultOnRecoverableError, formState = null;
        null !== options2 && void 0 !== options2 && (true === options2.unstable_strictMode && (isStrictMode = true), void 0 !== options2.identifierPrefix && (identifierPrefix = options2.identifierPrefix), void 0 !== options2.onUncaughtError && (onUncaughtError = options2.onUncaughtError), void 0 !== options2.onCaughtError && (onCaughtError = options2.onCaughtError), void 0 !== options2.onRecoverableError && (onRecoverableError = options2.onRecoverableError), void 0 !== options2.formState && (formState = options2.formState));
        initialChildren = createFiberRoot(
          container,
          1,
          true,
          initialChildren,
          null != options2 ? options2 : null,
          isStrictMode,
          identifierPrefix,
          formState,
          onUncaughtError,
          onCaughtError,
          onRecoverableError,
          defaultOnDefaultTransitionIndicator
        );
        initialChildren.context = getContextForSubtree(null);
        options2 = initialChildren.current;
        isStrictMode = requestUpdateLane();
        isStrictMode = getBumpedLaneForHydrationByLane(isStrictMode);
        identifierPrefix = createUpdate(isStrictMode);
        identifierPrefix.callback = null;
        enqueueUpdate(options2, identifierPrefix, isStrictMode);
        options2 = isStrictMode;
        initialChildren.current.lanes = options2;
        markRootUpdated$1(initialChildren, options2);
        ensureRootIsScheduled(initialChildren);
        container[internalContainerInstanceKey] = initialChildren.current;
        listenToAllSupportedEvents(container);
        return new ReactDOMHydrationRoot(initialChildren);
      };
      exports.version = "19.2.7";
    }
  });

  // node_modules/react-dom/client.js
  var require_client = __commonJS({
    "node_modules/react-dom/client.js"(exports, module) {
      "use strict";
      function checkDCE() {
        if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ === "undefined" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE !== "function") {
          return;
        }
        if (false) {
          throw new Error("^_^");
        }
        try {
          __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(checkDCE);
        } catch (err) {
          console.error(err);
        }
      }
      if (true) {
        checkDCE();
        module.exports = require_react_dom_client_production();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react/cjs/react-jsx-runtime.production.js
  var require_react_jsx_runtime_production = __commonJS({
    "node_modules/react/cjs/react-jsx-runtime.production.js"(exports) {
      "use strict";
      var REACT_ELEMENT_TYPE = Symbol.for("react.transitional.element");
      var REACT_FRAGMENT_TYPE = Symbol.for("react.fragment");
      function jsxProd(type, config, maybeKey) {
        var key = null;
        void 0 !== maybeKey && (key = "" + maybeKey);
        void 0 !== config.key && (key = "" + config.key);
        if ("key" in config) {
          maybeKey = {};
          for (var propName in config)
            "key" !== propName && (maybeKey[propName] = config[propName]);
        } else maybeKey = config;
        config = maybeKey.ref;
        return {
          $$typeof: REACT_ELEMENT_TYPE,
          type,
          key,
          ref: void 0 !== config ? config : null,
          props: maybeKey
        };
      }
      exports.Fragment = REACT_FRAGMENT_TYPE;
      exports.jsx = jsxProd;
      exports.jsxs = jsxProd;
    }
  });

  // node_modules/react/jsx-runtime.js
  var require_jsx_runtime = __commonJS({
    "node_modules/react/jsx-runtime.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_jsx_runtime_production();
      } else {
        module.exports = null;
      }
    }
  });

  // src/browser.tsx
  var import_react13 = __toESM(require_react(), 1);
  var import_client = __toESM(require_client(), 1);

  // src/avatars.ts
  var import_react = __toESM(require_react(), 1);
  function faceName(name) {
    const n = String(name || "").toLowerCase().replace(/^crew-/, "").replace(/[^a-z0-9_-]/g, "");
    return n || "unknown";
  }
  var BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
  var cache = /* @__PURE__ */ new Map();
  function useAvatar(api, name) {
    const direct = name && api.avatarUrl ? api.avatarUrl(name) : "";
    const [url, setUrl] = (0, import_react.useState)("");
    (0, import_react.useEffect)(() => {
      if (!name || direct) return;
      const n = faceName(name);
      let hit = cache.get(n);
      if (!hit) {
        hit = api.get("/embed/avatar/role/" + n + ".svg").then((r) => {
          if (!r || !r.data_url) throw new Error("no data_url for " + n);
          return r.data_url;
        });
        hit.catch(() => cache.delete(n));
        cache.set(n, hit);
      }
      let live = true;
      hit.then((u) => {
        if (live) setUrl(u);
      }, () => {
      });
      return () => {
        live = false;
      };
    }, [api, name, direct]);
    return direct || url || BLANK;
  }

  // src/api.ts
  function fetchApi(base = "", fetchFn = (...a) => fetch(...a), directFaces = true) {
    const ack = async (path) => {
      const res = await fetchFn(base + path, { method: "POST", credentials: "same-origin", cache: "no-store" });
      return { ok: res.ok, status: res.status, text: await res.text() };
    };
    const call = async (path, init) => {
      const res = await fetchFn(base + path, { credentials: "same-origin", ...init });
      if (!res.ok) throw new Error(path + ": HTTP " + res.status);
      return res.json();
    };
    return {
      get: (path) => call(path),
      post: (path, body) => path.startsWith("/ack/") ? ack(path) : call(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: body === void 0 ? void 0 : JSON.stringify(body)
      }),
      ...directFaces ? { avatarUrl: (name) => base + "/avatars/role/" + faceName(name) + ".svg" } : {}
    };
  }

  // src/key-scope.ts
  var EDITABLE = '[contenteditable=""],[contenteditable="true"],[contenteditable="plaintext-only"]';
  function isEditable(el2) {
    if (!el2) return false;
    const tag = el2.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    return el2.isContentEditable === true || !!el2.closest(EDITABLE);
  }
  function isCrewKey(e, root) {
    const n = e.target;
    const t = n && n.nodeType === 1 ? n : null;
    if (isEditable(t) || isEditable(document.activeElement)) return false;
    if (!t || t === document.body || t === document.documentElement) return true;
    return !!root && root.contains(t);
  }

  // src/components/Board.tsx
  var import_react6 = __toESM(require_react(), 1);

  // src/data.ts
  var import_react2 = __toESM(require_react(), 1);
  function useBoard(api, intervalMs = 2e3, query = "") {
    const [board, setBoard] = (0, import_react2.useState)(null);
    const [error, setError] = (0, import_react2.useState)(null);
    const [loading, setLoading] = (0, import_react2.useState)(true);
    const [tick, setTick] = (0, import_react2.useState)(0);
    (0, import_react2.useEffect)(() => {
      let live = true;
      const load = () => api.get("/board.json" + (query ? "?" + query : "")).then((b) => {
        if (live) {
          setBoard(b);
          setError(null);
        }
      }).catch((e) => {
        if (live) setError(String(e && e.message || e));
      }).finally(() => {
        if (live) setLoading(false);
      });
      load();
      const timer = setInterval(load, intervalMs);
      return () => {
        live = false;
        clearInterval(timer);
      };
    }, [api, intervalMs, query, tick]);
    return { board, error, loading, refresh: () => setTick((n) => n + 1) };
  }
  function useCard(api, id, intervalMs = 2e3, paused = false) {
    const [card, setCard] = (0, import_react2.useState)(null);
    const [error, setError] = (0, import_react2.useState)(null);
    const [loading, setLoading] = (0, import_react2.useState)(true);
    const loadRef = (0, import_react2.useRef)(() => {
    });
    (0, import_react2.useEffect)(() => {
      let live = true;
      setCard(null);
      setLoading(true);
      const load = () => api.get("/card/" + encodeURIComponent(id) + ".json").then((c) => {
        if (live) {
          setCard(c);
          setError(null);
        }
      }).catch((e) => {
        if (live) setError(String(e && e.message || e));
      }).finally(() => {
        if (live) setLoading(false);
      });
      loadRef.current = load;
      load();
      if (paused) return () => {
        live = false;
      };
      const timer = setInterval(load, intervalMs);
      return () => {
        live = false;
        clearInterval(timer);
      };
    }, [api, id, intervalMs, paused]);
    const reload = (0, import_react2.useCallback)(() => loadRef.current(), []);
    return { card, error, loading, reload };
  }

  // src/host.ts
  var import_react3 = __toESM(require_react(), 1);
  var CrewHostContext = (0, import_react3.createContext)({});
  var useCrewHost = () => (0, import_react3.useContext)(CrewHostContext);

  // src/mark.ts
  var MARK_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB2aWV3Qm94PSIwIDAgNjQgNjQiPjxzdHlsZT4ub24tbGlnaHR7ZGlzcGxheTpub25lfUBtZWRpYSAocHJlZmVycy1jb2xvci1zY2hlbWU6bGlnaHQpey5vbi1kYXJre2Rpc3BsYXk6bm9uZX0ub24tbGlnaHR7ZGlzcGxheTppbmxpbmV9fTwvc3R5bGU+PGltYWdlIGNsYXNzPSJvbi1kYXJrIiB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIGhyZWY9ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBRUFBQUFCQUNBWUFBQUNxYVhIZUFBQVFVVWxFUVZSNDJzMWJmV3hjVlhZLzk3NzNadnlObmNRMmdaQ0ZoSUtXTE5rQTNRM2JzaVJwVnl5c3VpU0FKcWpidEJUVVpIZmJyaWlpNlc2N29vTlhyVmFzRmdVSmhKcHVWS1NHRU5WVDFpUkVRNFJJSnc3WlFCeWJPSVRZanJPeDQwbG04SXp0K1o1NW4vZWUvdUgzSmpmamVlTUpjV3llOUdScjNzeTk1M2ZPdWVmN0VaakRDeEVKQUVnQXdBZ2g2SHgrKysyM2UzZnYzcjJpdmIzOUR4UkZXZUgxZW05c2FtcHFIQjhmdnhrUmFYdDdleVNSU0dpRWtERlZWY2NZWTBQUFB2dnN5TUdEQi9YWjFyN1dpOHdoY0VvSVljNW4vZjM5ZHl4YXRPZzc5ZlgxRzd4ZTcycEprcjVTVTFQanJXWTlYZGQxeTdMQ2pMRlBKaVltamhtR2NmQ3V1KzRhRnZhVEFJRFBKU091QmJ6ay9MOWp4NDdtQ3hjdWJFMG1rOTJhcHBrNDgrS0lhTTF5czlJZmFacG1aclBaN2tna3N2WEFnUU10NWZaZUNPRFVsank4L3ZycmJXTmpZeDM1ZkQ1Y1FydkpHSE5BY2F6KzR2WnZMRVM4Z3BHRlFpRVNpOFU2M243NzdUWUFBRUlJSUNLZFYvQ2hVRWgyanRESXlNaFBzdGxzVktEUmtlVFZBSzZHSWM2NmlJaVl6K2VqNFhENEp3QkFiWUhJODRHZE9HclgxOWUzT3AxT2Q1ZEltMStGVk12ZHMycUx2VWRSSzVMSjVMRyt2cjdWd3BFZzEwdmxpYU5xRnk1YytCdFZWWE5WQU9mbDFMakt5NnlrU1NJak5FM0xYYng0Y2F0QVo5Vk1xRXB0L0g0L3BaUnlSTVJvTlByYTBxVkwvODUreEFCQXBuVEdFZVQyTGR1dUMzVERBTWFzVWRNd0wxaVdkWWxTR290R293QUEwTmJXQnB6emRrVlJsbm05M2x0bFdiN042L1dLdERGYnNzV05LS1hFWHA5NXZkNzZaY3VXL1djc0ZydVhFUEszMDN4QU1pZGV3dS8zVTBJSVBQWFVVelh4ZUh5L0lCMWVRZUtJaUtocVdqYVZTdjEyYkd4c1cyOXY3OTErdjk4ejIzNCtuODl6N05peHU4Zkd4cllsRW9tdVFrSE5sdGdYdDMxTlJNUllMUGJ1a1NOSFdrVWpmYzFxLzl4eno5VW1rOG4zN2MwTUY1VVZEZFJJSkJMNVdlaWpqMjUxOFI2eXl6MURsVDc4c0hmNXhNVEVQK2J6K1pGeWV4VTV3RGtpb29xSWVQNzgrZWV2MlREYTRDVUFJQk1URSsrNmdiYzN0dXl6bUloRUl2KzhhOWV1UnRGWGgwSWh1VnFKT0V5M2YxUDA4N3QyN1dxTXhXTGJDNFZDeW1HQ3ZUZUt0S1hUNmQ4Z291ZWFYYVBEdmZIeDhkZmR3TnVHaUNNaVRrMU43Zi80NDQ5dkUzL3Y5L3ZwSEJuZm9pUVBIVHEwY21wcXlqbUtYRFNHMld6MnY3NklJWFNON3M2ZS9mMjJDbXJQRUJFTncrQ1hMbDNhTGdLLzVyTlhCU011WHJ6NE04TXdITmNxZ3I5QzAveCtQNzJxaUJFUktTRUVUcDA2ZGFlcWFxcUw0V0cyeXVjSEJnWWVjNWcySHhHWkRWQUNBQmdjSEh4VTEzVTFuVTd2RldpNEFueEp2bEsxOUdrcWxmNnduTUZ4MU40d2pQVFkyTmdEOW0rVUJRakZaU2NnZSthWlp4cnRrSmlVUnF1aFVPaHJseTVkZXFVcUpnaXEvMFBCM2Mxd2M3cXVXOFBEd3c4dEZIaFJHeXFGNnNGZ2NHVTZuUjVGUkJ3ZEhmM3ppZ21VWXpnNk96c1g1ZlA1bUszbXJFeDBocU9qb3o5ZWFQRGxraklSWURBWVhKbE1KaTg0V3F5cTZxVmdNTmprYWlBRnEvK3ZMdEszN0VCano1Y0Z2SnRHN04yN2QyVXFsYnBnSDlsaUtCNE9oMThvR3g4NFhPbnE2bW91RkFvVFF1SWlHajFXS0JRaWUvYnNhVUZFT2hjdTducG93cEVqUjFhblVxbFJBYnhEUDgvbjh4TmRYVjNOTTdUQTRjalkyTmlQSzBrL0hBNy9vQ1FkL3RKY0RrMzkvZjEvNllMQjBZSy9GekVUUndNSUlTU1ZTcDI0NFlZYjdyRVRHUWtBZ0hQT0thVTBrVWg4dW5qeDRuc1FFUWdodkxJNGdQZ0NQaHB2amM5SlBOQTIwWWFCTXdHRUR1QlZ1SENleldhUE5UUTBmTXRPb2lRaG9hTFpiTGEvcWFucEQrMXNDWXZuNXVUSmsydE0wK1JsZkw2RmlEZzBOUFRrYk5MM281LzY4Zm9kamRuV2QyZ2JHaHJ5dWVRTTNEUk5mdmJzMmE4N0RKUDcrdm9rQU9DMzNITExuOG15VEFEQUV0SmtEZ0JTTHBlN3NIZnYzbjIycHJDeVdWeW5UK29nSFF3QTREdnZQM3FUcWNoM1VZNDNXZGExUllXeVRKQlRFbFZNYTZDRGRFU2R2UUtiQXpQbzJMQmhBME5FOHVLTEwrN2J2bjM3U0gxOS9Rb2JnOE0wSnN1eTNOemMvRGdBbk9ycjY1T0lvemFaVE9aM2pZMk5mMVNpTmhZQXlCTVRFNzlzYTJ2N0YwU1VDU0ZXT2NsMGtBNys0SHVidmtXOWREc2cvaWxWcENZaXpVMUVqQllDTjFtV1VEakVMWGlwKzZHdWo1MDl5M2t6UW9nVmk4WCtyYTJ0N2VjbEFtVUFJS1ZTcWVNdExTMzNJeUtsaEJBZURBWmJ2Vjd2M1U2dFFWaFA0cHhESXBIb0FnQVNDQVJLQ3d6RWxqeC84UDFOdjVCcTZPOGtqL1FZY0dpeUNpWTNzNlkxRjdlbG1od1FHcWxIM2tSbGNtejkrNXY4SGFTRCt6cDlNMHBnRG8yUlNHUWZZd3dFWVJheDFkWFZmZTJERHo1b0o0UndDZ0N3WXNXSzFSNlBwOUZXRnlLb1B5a1VDcEdkTzNkK0JnRG84L2w0aWRyVHdPWUErL2JCamE5NG03MHZjSU9qbVRNWU1rUkNDQ1VFNUxtNUNVV0dhT1lNeGsyT1NyUDN4VzhITjc0UzJCeGd2azRmTFNtb2NBQ0FOOTU0NDFOZDE4ZHNQRnpvZ3pDUHgxUGYzdDYrcHNpUmxwYVd1d1RRWWxrTEdHTTlPM2JzVUJGUkVrdE16amw4OE9DanozaWJhNTQxa3JvSkNJUVFJZ0c1RG9WSllxK05RSXlrYm5wYnZNK3VQL2pvWDloTUtFcVpFSUtJS0wzNjZxdTZxcXI5WlhBaEFFQjdlL3VxSWdNSWtiN3F0cStxcXAvTzZDSWhrTURtQUgvZ3dBOWFDQ0cvc2dvR0I4RHJBN3dNSXdCUXNsU0xJNlU3MW9VMk5nZDhBUTU0eGQ0RUFDQ1R5Wnh4VzRZaGZyWElBRVdSbDd1MXluSzUzSGtBZ01PSER4Yy9XM2Q0blFRQUtNbnFGcVhSdTVqcnlBSElQRWFHaEhLRGM2WEIwOG9OZUJJSW9FMFRpTFFpNHFCYk8xQlJsR1dDQnRBbGR0QkRTZzJHcnVzUkFJRDE2OWNYMWI5N2ZUZTN1d1RmUjRZSUN4UVVJME9rQ0J0dCtvcHE3dEJxR01hbFVzTmV4TWg1bTZBQlVwMWRhblk0NTNBS0xjdEtpbWZIVmtKK1grODJCUUJYY3BNUkFqanZMQ0FFS2JjWUFZRGJmVGp0aVFRTlJodkhKT2NjSFN3aXh0cmFXa1ZnZ0lKWExrNFFBSWhwV3JoMDZkSnNTWmdMQUFDZXFZa1dBTktLSEFHUWtQa1hQeUhJRUlCQVcveXcybktGaU95cm9hRkJZNHhodWFQdDlYcXh5QURPdWN0SkkyQ1E4dUE4SG00Z29MSGdXU0NBQlNCWjVaNlpwa2xkeUhlMGZKb0JtcVpCQ1NNSUFLQXNTU1NmU0RUYkFRYXhuK0MwSFhnbkRVREdpVXdCS1BKNVIwNFFpVVNCSU1TN0Q2L0ppQ2Jjb1hWaVltS1JKRWxVakc4Y2pMbGNqaFFaSU12eWxIMCtzQ1FPSUxJc3R3SUF0TGEyRWpFR0FFS1FBSnlpQ2tYazh6K29nRWc0OVZCRUlLZWdveGdWb2tqcmtpVkxXbXdOUUtHbGh2WXhUeFlaWUJqR1pJbWhLLzR2U2RLdHRtV2RRUVRuNUMzZ1NBQ1FMSUR5RStCSXFFVGVMSDNpME1vNXVjME5GMk5zUW5SMVliZHQ2bXZyWndSSmdjMEJCbjQvL2ZEajFlK1plYk5Ycmxja1JMRG1UL3BneWZXS1pPYk4zc05IVjc4SGZqOHRseDAyTnplNkJuZ21NMGVLREdDTW5YWUxHRHcxbm51RlRPcHl6TDFxZ0VCSEJ5Y0V0cUxKTmFwUUdSSFpQSlMrR0pXcHpDMnVJOUlmUWtjSDk2MGFLTlZBYmx2NnI3c0ZlRnBCTzFka1FDS1IrTXkyaWpNeUowVlI3dW5zN0x6WmpyR0pxQVcrVHAvVS9kMTkvVXhqVHhBSk5MbHVXaE9tR1lGOEx1L3B1aDVZY3AwaUVRa01yckxIUDN5azY1UFMyb0JkcytEQllMRFY0L0dzS1pQaFVrU0VWRDcxYWZGQmYzLy9rS1pwc1hLWlUxMWRYZTM5OTkrL1RoaFRnMUltSFBuZXZxQ1Y1ZXVRNFFtbFVaR1ZCbzlFUFRLbGlrU3BSNXIrVys3MlZQRmNrU2oxeUZScDhFaEtveUp6eGsrWkJmTlBqbnh2WDlDbE1DSWhJbG0xYXRYNm1wcWFScmc4V3dCMlVFUlZWWjNxL2FoM3dIWW1LQkZDV0RxZDdtcHFhdHBvMXdDZGVpQ2psRXFwVk9wQVMwdkw5NTN2bHFzR0JUWUhHUGg4MG9ZZnNTYzU0T01FWVJWeTlDSldTSkFRZ0FCeUpCWHlDQUpBQ1doQTZXZEE4QjNzVHZ4UGQwZTM1VllWY21pY25KenNXcng0OFNZSGc0T0hFQ0tsVXFtRGl4WXRlZ1FSSmRuaHp1VGs1QWROVFUyYlJGZElwK05Hckt1cmU2aW5wMmNGQUl3NkZhUlNUYkFyTkN3VWdMY0E0QzAvK3VtQnZzOHJOeVg3QUJydU9JdjV4anNyZXBHKyszWmFJS1Rpemw0dWZRRis0TUNCcjlUWDF6OE1BRWlGOFJVSG02cXF3U0o3bmFMby92MzdsMnVhVmhCYVlGZVVrNVBKNUNzVlcwdE9oUWg5a3BpZno5WGw2L1JKUHZSVkhJSnlTdDNoY1BqbE1xVnhiamQwOVZBb2RPc1ZyVFVIMU5UVTFEdml1SWs0M2FYcmV1SG8wYU1yeFdHcFdUUDNhZlcvdHZ2eUdsVTFSb0xCMERKN3JJYVhFU1Nmbkp3TXp1Z3JPZ3c0YytiTUl5N2xaQXNSTVpGSS9HL1oxdEtYb3pNa0F3REVZdkUzSzJFWUdocmFXTGE4ajRqVTUvTkpoVUxoazlKaEozR0I0ZUhoSjc1c1RCRDZBUTh6eHR6QTgzUTZQZWozKzUwQkRsSjJrZkh4OGNkY09NZ1FrZVh6K2NtalI0L2V0Q0FqcXU3ZElOaS9mLytTWEM0WEtkUFhMR0laUEh2MnJ5czJkMnhBTkpQSkhLK2tSdWwwK3FqRHlZVnNrZ3FEWEhJNm5YNS9GcHI3Nzd2dlBzWEc2Sm9qUzNaZzlJQmxXWWlJWnNra1ZySGpPalUxMWVVRUhRdWhDZmJzRHdVQWlNZmovMTJ1SVdyVGJqTEc4UFRwMHh1cThHS1h2M0R4NHNYWFhicXN4YytpMFdpWEV4M081K2k2dUZjNm5mNlAyZWlNeFdLL3FacEdSNkk3ZCs2c3kyYXpBMjZEaWM3aTZYVDY0SjQ5ZTVZNGh2RjZUSWhkV1FhWk5yNDdkKzY4WVhKeWNsOEY4QllpWWlhVCtmM3UzYnVicm1weXRMT3pVM0k2eHBxbWFTN2pNaWpNNTUwN2ZmcjBINWNZMUxsa0JBbUZRckpUM3VydDdWMmJ6V2JQdUlHM0I3a3NYZGYxbnA2ZWI0aVlydHExakl5TVBPbWNKWmM1WFFzUlVkZDFJeGFML2VLMTExNXJFSDN6dGRnSCs1d1hMZmEyYmR2cW90SG9DNnFxNmlVVElHWG5oa2RHUnY2cW90V3ZOcmdZSFIxOWJwWWhhU2JNQ1o4OWQrN2NWcC9QVjF0eXJHUm5sbER3dzhYYk9YcjJkNjQ0U2o2ZnJ6WWFqVzRScEk0dUdsa0VINGxFZmpvbjhVcHZiNjhDQUpCTUpwOFg0NEhaSnNXejJleFFOQnI5ZVU5UHo1M3V0WDBDcEVKRi9kQ2hRM2QrL3ZublA4MWtNa096VFl3N2FvK0lPREF3OEt0cXdaTnFOWUVRWW8yT2p2N0Q4dVhMZDlnSkZpdXREd2pWR0hTZTZicHVxcHJheXhuL3Yxd3VkendXaXcyZk9YTW05dlRUVDJmRUlzWExMNy9jdEhidDJ0YjI5dlk3R3hvYTF0YlYxVDBveS9MYXVybzZSYWhJa1pMaUJnalBKTnNsYm05dmIvKzEyeXpERjJLQXlJVGg0ZUVubGkxYjlrWnRiVzBqVEE4ZnVHVm80a3NUbDB0Um1zWTU1MGxFVE9xNmpvZ0lYcStYRWtKYUpFbHFycW1wS1FWbzJhQnB1ZHErRFZMV2RUMGZEb2QvZE1jZGQ3eHAwOHBtdGtybUtPRTRkdXpZM1psTXBxZlMvTDdMYXpOV0ZhL0tXTE85TGxONkZES1pUUCtwVTZmdW5aY2N4YkdvRHovOHNEY2FqZjY3cXFxR0NMUTBjaXpIRVB1OE12RVdSKzlkZjNqNTNRU0dpS2lxcWhXUHgzKzVaY3VXK211eTlsODBBUUVBNk9ucHVXZHljdkxkTXZFQnE0SVpzNzh2TjcwR0svWDNxVlRxd0lrVEo3NVprc2ZNZDNQcWNtZ1pEb2ZYSlpQSmZacW1XV1hjVXZGMXVFcE1zWitWdmw3SGhUZElXVEtaZkhkd2NQQzdZbGg4bmFQUHFpb3hSZTRmUDM1OFRUd2VmeW1YeXcxV0FDdUN0Q3E0VnVTY1l5NlhHeHdmSDMvcDVNbVRhOXoyWGZDcnM3T3o5SVVKK2VUSms5OGNHUm41cDNnOC90dHNOanVvcW1yS01BeFhEVEFNQXpWTlMrWHorVE9KUkNJUWpVYWZQMzM2OURkRVQ0S0k5S3JEMnJsd2cxZWpFVEQ5Sm5tcEQ1WkRvZENOTFMwdE45ZlUxTnk0ZlBueW1zSEJ3WnNsU1lLVksxZEd6cDgvYnlxS0Vvbkg0NUVOR3paOFh0cUpzcTA3bjNWTTl5cXYvd2Z5Yk5pa2t1R043UUFBQUFCSlJVNUVya0pnZ2c9PSIvPjxpbWFnZSBjbGFzcz0ib24tbGlnaHQiIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgaHJlZj0iZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFFQUFBQUJBQ0FZQUFBQ3FhWEhlQUFBU1gwbEVRVlI0MnMxYmVYU2MxWFgvM2Z2ZU55UEpsdkVpNzhhN0xiekpKa3FLU1JQa3BDU0IxQmdLa1JNYWNwS1FsbEtXSkNTbEpVMDVZamc5elVKeW9BZVNBQ1doVFZOYUxBNWdsNEJJbWdRVGtoRGpnRzNBZUYrMDJwSmwyVm9zelh6djNkcy81aHY1MDJnazJ5QTd2SE8rNDJQTnpQdmVYZDY5di91Nzd4RkdkaEFBQThBRDBOd2ZiNzMxMXVTR0RYVnpoWGdCMU05VjFTa24raktsaWNCT0p5Sk9wOU5OSmNWRmZhcDZVQlFIUnhjWDc3anNzZy92dS8vKys5T25tbnNrRmp4UzgzQzBPQkFSWnM4dVg1Z08wNWM2N3o2a2dnb3ZmaFlSSnhVQU5MdCtIYlFJQXFBZ0lBM21laVo2TlpHd3YwMlVKT29PN055eFMwK0tiUURJU0NoaUpCU1Fzd3FXTDE4K3R2WEk4V3BSdWk0TU0rOG5JcXVxMEpNcjEyamhwNk5NRUJHSUNLcnFESnZmSnBMQlQ4YlBuUHJFNnkrOTFKSC83aitHQWpnU1NPZk9yWmpVMWR0eHN3bytyNnJuaTJqT09DNTZSL3c1bmFFbkgxV0FMRUJnSmhDaE9abElQakpoM0tqdmJkdTJyVFcyRmptWENyQUFuS3JTckZrTGIrbE45MzdOQzZhcUNnRDEwYlE4Z2xzczhod0ZRSWFZUVlTV1JHQy9jY01YUHZ1OVZDb2x1VFdkYlFYMDcvVTVDeGRXZEIvdnUxOVVMeEh4T1d1YlllYlV2R2VvK1UvbExSb3AyUkl4ak9YZmpTNHF1bkgvL2wzYjNrNXNvRE1VbmdESWpCbHovcW8zNCs0VGxWRXE0b2hvS01FMXRpQ2JtNFlvbWk3K0M5VW9OdWJXcmc3WmIvTFFjNnNIMkRKVHo2aVM0dHZxRCt6K3Q5aDNkU1FWd0FDRWlEQjUycXdId3REZExDS0lBcEFwOEgySkhrdEVBRkgyUmFyN2d5QTRRS0JHVVRtY1NBUUFBT2M4UkdVeWdXYUV6czBHTUNmNzlmNEE2dVBCTVc5NEFJYVpZUVA3NEtIRy9UY1JrZmFubEJGUUFBT1FtcHFhb29jZStZOTFtWXk3UXRRN1FrR3JLNkRTdjArQmJtYit1VTBFZGNYRjluZVZGUlU3bjNpaU5xTTY5R0krVVYyZDJMWnRSM2wzdXUvaVRGLzZjbEc5VkVWSHgrSUxEL0ZlVDhRMm1VdytzM3pwd3V2cjZ1cmFUN0hkVGtzQkJJQnV1KzIyNU9PMTY5ZW5NK0ZIdkhjaEVRVkRXWUtZWVpqMjJ5QjRlRXhKNmYvczNMbjFRQUdGOGhEdmsveG92bmh4NWN6TzdzNjE2VXpmVFNJNlp6alBVOVUrYTRPaW9xTGc3eG9QN3YzdTZRUkdPbzJBSjFPbXo5NFFobTYxOTM0STRkV0QyREJSUnlJSTdubGY1YklITm16WTBCWEwxUlNMQlhxYXNTYVhaajBBckZtenBuVHpxMi9jbU02a3Y2Nks4MVRFSXh0N2NpTms1c0I3ZWVSWWUvUE5rZUR5VHJhQUJlQ216cGo3L2I1MCttOVZwSkR3Q2dETWhveWgveTBxTGZwUy9hNWQrMk8vbDdlYm53dEFZQWNBOCtjdm1kZlowMzJ2OTNLRmlNOHAweE96VmU4ZjdXaHZ1ZjVNQWlFTmgrNW16N3ZnaHE3dW5vZkUreEJBVU1CZG1abTF1S2o0SDVvYTl0d1RCU3c3MG5nOVh4RkVoR2t6NXR6Um04NzhpNG9vRWJPcWY3VGpTTXYxY1lBVzIzSTBGR0trb1lMZTdObmw1ZDBuZXJZNDhRRU5EandDZ0luNFJFbEo4WFdOQjNjL0ZTMU9SOERpcHhPVUNZQS9mL2E4TlNkT3BCOVgxYWVQdGpWZFd3QUh4QkZpd2F4UUtCaFJUVTBOZC9mMlB1SkZpNklFUm5sdVR3QTZGZjVqa2ZCQnBPR3pMWHhPK1I2QWJUaXdkNE1KOUtLSjQwZmZFUHRNNDF2d2dvcUtwZE5tekxrdnR1NUJyajdJOWZjZGJMNGhETjFOcXVKT0FwaVR3SWFaZFZSUjhWV0hXK3AvRlFrZjR0d1BBY0E5WFYySDJ0dmJNd00vcXJMQVFWZFpXVG52Y091eHVqRDBsNDBkVjdhcnU3UGo5WmluRHRvQ0JBQXJWNjRjdCtkQTAxdmUrYkxCWHFLTzJkaGtzdWltNW9ZOVAvZ2pDbCt3S0lzYnNiS3ljbDVEeTVGZmhKbHdGZ0J2akRrMGQ5YlV4WnMyYmVxS0IwaVRGL1VGWEhSN0puU3JvWnFmYXoyUnNZbkFQdGJTdE85cjd4TGg4eU05QTVBbFN5cm50YlNkRkQ1TE10RFk3dTdlM3U2dVl4dGpHYXJmdWdUQVYxVlZqZTFMcDIvVmJEM0xlZTVHeG5Eei9MbExib21USCsraXdRQjB6c0tGRlcxSDIvNHZKcndCd0NxaW9YTmZYTDU4K2RnWXRPNFgwZ0RRM2ZzYXJsVkZXZlNGdUFLVW1UbVpUTnorMGtzLzdYZ245ZmZaVmtDbXp5LzNYbVpEMWNVOE9HZXdzdGIyenVzaXJ6SHhHRUExTlRYMC9RZC85SXJ6Y21FV3ovZi9XQUJpSnRwMnkwMWZ1RENWU3VHVXdpdW91cmFhV3llMmpnZ2ZNS2x0a3RhK1dhdEluVkxwVENDWk1IbjZiNzNYaTdPMVE3OGNIaUJtUTF0dXVmRUw3MDJsVWdwQSsrSHVyRmtMVm5UMzlyNGFZZTM0d2owem01Sms4bE1ORFhzZkh3NWYxMmdOQTBDS1VtZkZPMDVqZmd2QVRaODVwN3F2TDF3bldhTENEUFJrUW1sSnlZVUhEdXplQ29CdERqejBwdE9yVlVHUmNEYTI5dzBCQitiT25iRytvV0h2a0lpcWVsMjFTVkhLQThDbFAxc3pMUXpzWWhhZDVweStJeSt3bGxTWW1vUFFiVTlScWpuM3J0cTF0WDZJZ296ZWY5RjcxLy95eGQvdEF6QTNseTV6bjZ1UzdVMW5yZ2F3TlpJTlRFUXljZkxNMzRUT3ZUL1BiUndSV3h2WWI3UTJIL2pIb2F4Zm96V2NvcFJjOHR4VkYzT1NiNGZxbjNGZ3hwQVpHVVpNblVKQzMwV01YNGpEdHpaKzlLbVhjKzhjeWdzbVRwMzV6OTdKMS9Pd2pBZklXTXUvUDNLNGNhV3FNZ0hBaWhVckp0WTNIOW1ySXFWNWlFbVptWXBIbGZ4SjQvNWRtd3RFZjZwZVY4MjFhMnY5SlQrNzZtNFQ4RDl4WU1qM09vZ1hBV2lFdG9JeUcyWlRiQ0VacitvazljSkhuMDVGbnBCUGdSa0Fmc2FNT2UvcnpZU2JKSnZSNkNUdkJETEVQVk1uVDUvM3hodS9QOHdBMEhxMHM0S0EwbHk2aTZjK0ltcWE4ZDdsYnhUQytUbmhQMWgzNVgzSnNjazdKU01hZG1lOGVsVWlZaUxZa1htSTFhdUczUmt2b1dnd05ublhCNSs5OHI3YXRiVytlbDAxRjBDSVdMcTBmSnVxSG95VjRsbW1IZkFnR3RYZGUyeEZmeHIwb1Z1c3NSL25KaUppQU5qMGNtMXRiejZFek8zRFMrcldYSjhjVy9TbFRFYzZoSUtJeUlCR2pBMk80OVRzM0FyS2RLVEQ1TGprbDFiVnJmbDBwQVNUQjR4TVhWMWRPZ2pzRnNvU2tKTEhIaUdUeVN3NWlRT1lGdzFWdkJybWJZTmdzNEpxMTliS0I1NzV5M0ZFOUcxM0lpT0FuaDNCQ3lnQ1VPTjZuU2p6dlZXL3VuSnNiWFd0WkJ0S0EyRjlZSU0zQ3hXOHFvQ0lMdXBYZ0lyTzFLd0dhRUF5SjBKeFNYSnZWR0NjTERWZXFESUExTmplNjRMUzVBUkpxMFJjM1RrYXhKSVJDVVluSmtvR253UkJvelVOR003N3Q0Z0tVUUFLRVptUnRUMFRWTFVzOGdDS3Z3UlFpS0lwKy8rTi9UNnljZFhHckV1UlhxRmVGZWRROUlGRW5Db3JyZ1NBVmF0V1NYNTlZQ3czRmlqN1NWVkJSSk9ZR2F3S2lQY2xoVFVGSlphT3ZLS0RRSkRLelRjRWdNNlQwQk5CejdrS2lKVEZlUUl3djFxclRaUVNCMUJoenVzUnpkSlVBOGdRSW9JTFhhQ3FZRlZGbENyeUt5d1NFVDNVZXJ5clVPMlZhRzhiQjlCRUZRV1U2TnlibjBpOUFvUkpyUy8waml2RUFQYW1NMzB4QlF4TUZTS3FwK084aVVTQ0N2OWRNZ3JOdkF0cVlRZVlndEJjVlU0cEh6TXpFb2xFdklXZDJ5Zkt6RlEyZnV6WUFWbUFzbnJldU9ycDR3QWRJc3NBNjdtdkRFbVZESU1VclJ0ZldOR1pGOEVJQUthWFRSaHZqR0hOZGxVbzFqOUFNcG1nS0FZb3ZKZjJxR0VYM3ljQ2dETHAzb241YWJCNlhiVUJrUkt3bFFOV0ZkSnpibmtsNFFTcmdyWWlsWklJQ3d3NGM5SFYyek11Q25nNjBHa0kzbXRIZnd4Z3cwZG9NTHNTNVVXZVBTUXBKL1FZUkNtcUtzOTVFSUFvc2FHZkRBMFplRTRCMWtpSkFEYmMxaDhEaUtsK0tNRGd3bkJSL3Q5cjE5WjYxTlR3cjErdWVDN3NDVGZiVVlGUlBmUGUvTnUzUHB3ZEZaaXdKOXo4d2tzVno2R21oZ3RWaHk1MGl3cjJJWWxBcXZ2Njh5TXBYaThnUDZrcW5NaDdJamc1NEFYVlM3WVRVaWtod2w5cktIMGNzTlVzajNpV2hWZlBscTA0U2F2eTN5Q1ZrdW9sMi9OWEwwUUVFVmtleGJhQkFBK0VSREt4dTE4QmllS2lOeWc3dVJsSU1TbFVjT0g4aW9ycCtieDZEb052L05qNkxiN1BYME1HZmJZazZ3bFpSYWlNNUtPcVhoWE9sZ1NHRERMUzY2Lys5ZVZQdlZxQUd5QUFzbno1OG9taXNpTFh2Y3NIZUJ6WWJmMGZsTTg5ZndjSWh5bHI2bmdueFFOYW5PbnFxNHExcHBDdmhCYy92djVaMXlWVjZ2V1ZvRFN3d2VpRTRZUmxEZ3h6d21UL0xmUWtUdVB6d0RBbkxBZWpFeVlvRGF4NDJScWVDRC84NHNmWFB6c0VNV0lBVU52UjdsV3FLSTBUb0pFUkdVRDd0SW5qdHNmN2JYN2lsSmxQZWUrdmpGS0dPVW1Ga3pHR24yazcxSEFGaGppVjFiK1E2bXJ6b1J2OUp3VjZOU21XcUdoU2RaZ0NTUUdDaXRJd2RRUUJUT2dEOHhzZ2ZWbzNIbjE4WTJxakc0WVZpc3R6bFE2azl6MFJHV3ROWFd0TC9lVVJJMVJsZ1kxdXhzeDVOL2YyWlI0UThYRUdSYU9VR0U2WU1uN1I3dGRmMzU5WFh3OWloZUwvZitZUExXYllEZjBIWVBUQ25kcGRXajVzRnZsRDVVTU9zVlEyREJ2RUFIVFJvZ3RudGg1cDNlRlZrelF3aFRzaXRvRzFYenpjY3VCK0FMYWZGRjI4dUhMbTRTT0hkb2hvY2Q1K2QwUnNTNHFULzlwWXYvZkxHUDVzSGxWck5hTTJ5aFFqT0tyWFZSdFVBN1ZVTzl3aEtBdkFUWjQ2ODd1aGs2L2swV0VLZ0pnNVV6WnVRbmwwY0lNcDdqYVRwODE2T2d6ZG1zaHQ0ajlVWWtxUEh6TjIyWjQ5Yis0Ynlnc0dPVzlCRlA0MitqNVVDT2tYdHY2eVpjdW1OeC91ZUV0RVJ1VUJPQWVRQ1FKVDEzYW80ZU9xeWdBR1ltVWJtSWVpUUpoUExpZ1V4WjA5M2QrS0JaSlRMNTBHSFkwNzg0ZE82MVJKdndKYTJ6dS9xWXJSZWZRZVZKV01ZU3BKRmowVXBVYU9wd2NQZ08rOTU1cy9ZNkxYQ3BDZlJsVzljLzZhS2RQblhKTkhuYjhiaGdYZzVzMWJmSmx6L3RNaXZrQmZreGpBanM5Kzl0cWZJblpnZ3ZJbm1UUjExbDk0TDA4V21FUUF3QmpUTVdGYVdjWE8xMTVyZnBlMHlCaUFWRlpXbHRVM3RXMTF6azB0NEtXZW1FMWd6ZWNQTngvODl6aTlILytTQThDSG13K3NaNlpOeUI2RDgva3U1a1VtdERjZldWZFZWV1hQWUR1Y1BZWXcyOWF6Qnh2YkhuUGVUOHRyaFBUM0FnTERXNjljL2JIL3l2ZHVIb1NTaWFRb3NGOWxwa0tCeDBEVmV5OS91bnRmUSsyNmRldjRqNmlFL3FNeTMzdndoejlTbFkva05VUnplMStaQ2FQSGxONzI4TU1QaC9uc0VCZG9MWm1HaG4wdkpSS0pIeEJ4b1U2UUFjVDFwVE5YZmZtcmR6d1JLVUZRK01UbzJSb213dnN5dm16YWd5TDZHUkVwRkpjY3M3SFcya2YyN256elY0VlMrRkNMNXZJRmMzL1oyWFhpYWxWTXhxQjJPYkdLT085MWNkM3pQNy9vZ3ZMNWRTMHRMVDNSQXZRc3U3d0Y0Q3NyTHozUHExOG53S2MxYTNsYndKZzJzR2J2N1BNWFhkUFV0Q2NzdExaaGo4bk5XckI0UmZmeHpwZEZKQ2pzTWVxSTJMSXhlMHBLaWo1WHYyL1hiMklCZFNTUHlnMDRLemg3d1lLTGVqcjdmdVJGRnhjNHg1VHpmTEhHK3RKUnhSL1l2My9YSzBNQk9ETU0vTERIajdZMWwwMmNzdHM1VngyQkl4cE1uY09yYUprTDNXZkdqQmtYekpvNS9aVzJ0cmErbUNMd0RoVEJPSG4wVFZhdlhsMXlvay91Nk9ucGU5U0xUSWthdVFXRWg3ZldXaHVZNnh2cjl6NFhNd2hPVndGUjJxdXluY2RlZmIyc2JFcW44KzV5RWZFRmdCSURFRlcxb3FqcTdjdDg0cnl4NDlOTGwxendWbU5qWXlhRzVXeWVBcW5Bd3pHaGN3QklWcTVjV2F4YzlLbUQ5VTAvRHAxYjY3MFlvb0p4UjVFOXoyQnRZTzg0M0hUZyt6akZlZUhUQWFvQmdIRGNwR2xmTldTKzQ3MlhJUUpvcm5scU9IdWpZeWNiODU4bGlhSW5EaDdjdFZQMXpKeUFpTEIwYVdYNTBlUEhyc3BrMHAvM291VXFDa0NHT1RFT0lXSmpMZDNUMnRMdzkzaUhoNlVISWEzejV5Nzhjay9YaVh1ekZmT3dkd1UwcHdoVkNZMnhtNW40bDRtaTVPOU5BcnZPS3lvNnZHWExsczdjRCs2NjZ5NSsvdm5ueHh3NjFESFJBK1hlaFJkbG5Mc0VxaGVKYXFBblQ0Z1BlV2RBQVdPTlJTTGcyNXNiRDN3SHAzbUY1a3hLRlF2QXpadzUvNW9UbWZTajNra3BJQTRZOHJaSS82V0pxTFdiSTU0RlNoMWt1Q01SQkFvQW1UQmtpSTRUbGJGRXhKcnRWMEpWUUVRT3d4NnhWNWU5TmNJOW8wWVYzMWkvZjlkUHppUUluMkd0bHVVT3lzdVhMVHZhZWZ5SDNzbjdSQVUwdERmRXQ0Wm0yZU9UUjl4elYyUm9RR05KUGRCLzQyTzRpMWRlVlptTklXYmFXcEpJWEY5ZnYvZFZuT0hscVRNRUx3Y0ZnRzF2YnoxMHlRY3Uvbkg3MFdPc3Fpc1ZzS3FxVVMrQkN5ZzVzaUJ4ekNwS0JJMDRlODNMTER5TThENEtFc1lhSThsRTR0c1ZTeForN3JYWE50ZmpiZHdjbzNlUW5nUUE1aStxdUxDNzgvamR6c2xxRVlHSWdnaW5jTnN6SGdKQUZMQWMzVUZLV1B2VDBsRWxkKy9ldlgxVC9wck9oUUxpbHZWRVFIbjUwcXFPNDExZmNkNy91U3FNcWlEeUNvOHp1enc1Z0EvUUxHOUhSQXdpU0JDWVp5M1pCeG9iOXo0Zmg4VnZGMnVNUkVlSDQrWHlnZ1dMVjNUMTlGenJ2S3dCY0lIa2JuNE5USVA1OXdkelBYdk9MU3RyYU1vMU1IY2trc0dHa2tUeXYzZnYzcjZsMEh2ZmlSVkhza0RwUDBoVlUxTmpINnQ5K2oyOTNWMnJuTmVWenJsRnFqSVZvUE55Y0MzT1ZwOE1oSHFjUUUxc3pIWnI3TXVqUzRwZXZQYmFUN3lXU3FWY2ZoVTRVaGo3YkpTcG5CK01hbXBxN0pOUFBqbWxxODlOUitpbkhPL3VMU291dHRNQklKTnhUV1BHakFrRjBsUmFaSnZ1dlBQT2xyVnIxL29DYVhnazdpQU5HUDhQd3hTVTZsNUVqMHNBQUFBQVNVVk9SSzVDWUlJPSIvPjwvc3ZnPg==";

  // src/css.ts
  var done = /* @__PURE__ */ new Set();
  function injectCss(id, text) {
    if (typeof document === "undefined" || done.has(id)) return;
    const el2 = document.createElement("style");
    el2.dataset.crew = id;
    el2.textContent = text;
    document.head.appendChild(el2);
    done.add(id);
  }

  // src/styles/base.css
  var base_default = `/* Ported from scripts/crew_dashboard/tokens.css: the only place a colour is decided. Two inherited inputs (host
   background and foreground); every surface, stroke and text step is the foreground at an alpha. Nothing here may
   reach a host page: the inputs sit on the OUTERMOST .crew-scope (a wrapper that sets --crew-bg / --crew-fg inline,
   Desktop from its theme, wins over them; a nested .crew-scope must not re-declare them) and on :root only when the
   document is our own served shell (#crew-app[data-crew-shell]). The ladder is declared on .crew-scope (and that
   :root), so it is recomputed from whatever colours the wrapper set. */
:root:has(#crew-app[data-crew-shell]),.crew-scope:not(.crew-scope .crew-scope){
  /* The page's own scheme, so an embedded mark (the header logo, the tab icon) picks the ink that reads on
     THIS field, not the one the viewer's OS prefers: a black-ring mark on a dark page is an invisible mark.
     The dashboard's field is dark; a light host sets --crew-scheme:light with its --color-* / --dt-* tokens. */
  color-scheme: var(--crew-scheme, dark);
  --crew-bg: var(--color-background, var(--dt-background, #0f1115));
  --crew-fg: var(--color-foreground, var(--ui-base, #e8eaed));
  --crew-font: var(--dt-font-sans, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif);
  --crew-mono: var(--dt-font-mono, ui-monospace, "JetBrains Mono", SFMono-Regular, Menlo, Consolas, monospace);
}

:root:has(#crew-app[data-crew-shell]),.crew-scope{
  --crew-text-1: color-mix(in srgb, var(--crew-fg) 94%, transparent);
  --crew-text-2: color-mix(in srgb, var(--crew-fg) 74%, transparent);
  --crew-text-3: color-mix(in srgb, var(--crew-fg) 54%, transparent);
  --crew-text-4: color-mix(in srgb, var(--crew-fg) 36%, transparent);
  --crew-stroke-1: color-mix(in srgb, var(--crew-fg) 14%, transparent);
  --crew-stroke-2: color-mix(in srgb, var(--crew-fg) 8%, transparent);
  --crew-fill-1: color-mix(in srgb, var(--crew-fg) 7%, transparent);
  --crew-fill-2: color-mix(in srgb, var(--crew-fg) 4%, transparent);
  --crew-fill-3: color-mix(in srgb, var(--crew-fg) 2.5%, var(--crew-bg));
  --crew-elevated: color-mix(in srgb, var(--crew-fg) 5%, var(--crew-bg));
  --crew-overlay: color-mix(in srgb, var(--crew-elevated) 92%, transparent);
  --crew-shadow: color-mix(in srgb, #000 50%, transparent);

  /* Desktop sets --crew-in-running / -blocked / -review / -ready / -done on its wrapper (theme.ts); a nested .crew-scope
     re-declares the tones below, so the inputs are read here and the browser, which sets none, keeps its fallbacks. */
  /* status tones: running and verified green, blocked/failed red, review/unverified/stale amber, ready
     blue, done teal; todo and pending are neutral. Every state chip on both pages takes one of these. */
  --crew-tone-running: var(--crew-in-running, var(--color-success, #34d399));
  --crew-tone-blocked: var(--crew-in-blocked, var(--color-destructive, #f87171));
  --crew-tone-review:  var(--crew-in-review, var(--color-warning, #fbbf24));
  --crew-tone-ready:   var(--crew-in-ready, #60a5fa);
  --crew-tone-done:    var(--crew-in-done, var(--color-info, #2dd4bf));   /* finished work: its own tone, not the grey of "nothing" */
  --crew-tone-neutral: var(--crew-text-3);

  /* a tone as a tinted box: the wash, its outline, a stronger header wash */
  --crew-running-fill: color-mix(in srgb, var(--crew-tone-running) 8%, var(--crew-bg));
  --crew-running-line: color-mix(in srgb, var(--crew-tone-running) 35%, var(--crew-bg));
  --crew-blocked-fill: color-mix(in srgb, var(--crew-tone-blocked) 8%, var(--crew-bg));
  --crew-blocked-line: color-mix(in srgb, var(--crew-tone-blocked) 35%, var(--crew-bg));
  --crew-review-fill:  color-mix(in srgb, var(--crew-tone-review) 8%, var(--crew-bg));
  --crew-review-head:  color-mix(in srgb, var(--crew-tone-review) 14%, var(--crew-bg));
  --crew-review-line:  color-mix(in srgb, var(--crew-tone-review) 35%, var(--crew-bg));
  --crew-ready-line:   color-mix(in srgb, var(--crew-tone-ready) 35%, var(--crew-bg));
  --crew-running-glow: color-mix(in srgb, var(--crew-tone-running) 55%, transparent);
  --crew-running-halo: color-mix(in srgb, var(--crew-tone-running) 35%, transparent);
}

/* the standalone page: the served shell has only <div id="crew-app"> */
body:has(#crew-app[data-crew-shell]){margin:0;background:var(--crew-bg)}
#crew-app[data-crew-shell]{height:100vh;height:100dvh;display:flex;flex-direction:column}

/* \u2500\u2500 scrollbars, both pages (scoped to the board/card root): a hairline track and a small rounded oval thumb in the theme's own tones \u2500\u2500 */
.crew-scope *{scrollbar-width:thin;scrollbar-color:var(--crew-stroke-1) transparent;}
.crew-scope ::-webkit-scrollbar{width:8px;height:8px;}
.crew-scope ::-webkit-scrollbar-track{background:linear-gradient(to right, transparent 3.5px, var(--crew-stroke-2) 3.5px,
  var(--crew-stroke-2) 4.5px, transparent 4.5px);}
.crew-scope ::-webkit-scrollbar-track:horizontal{background:linear-gradient(to bottom, transparent 3.5px, var(--crew-stroke-2) 3.5px,
  var(--crew-stroke-2) 4.5px, transparent 4.5px);}
.crew-scope ::-webkit-scrollbar-thumb{background:var(--crew-stroke-1);border-radius:999px;border:2px solid transparent;
  background-clip:padding-box;min-height:28px;}
.crew-scope ::-webkit-scrollbar-thumb:hover{background-color:var(--crew-text-4);}
.crew-scope ::-webkit-scrollbar-corner{background:transparent;}
`;

  // src/styles/board.css
  var board_default = `/* Board styles, ported unchanged from scripts/crew_dashboard/crew.css (the .page-board rules). The only edit: the old
   \`body.page-board\` rule is the root element's \`.page-board\` rule, so the board lays out inside a host page too. */
/* board page (ui-spec section 4): one-line header, crew bar, five fixed lanes, the desktop card */
.page-board *{box-sizing:border-box}
.page-board{margin:0;background:var(--crew-bg);color:var(--crew-text-1);
  font:13px/1.45 var(--crew-font);-webkit-font-smoothing:antialiased;height:100%;display:flex;flex-direction:column;overflow:hidden}
.page-board button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
.page-board header{display:flex;align-items:center;gap:14px;padding:14px 18px 10px;flex:0 0 auto}
.page-board h1{font-size:15px;margin:0;font-weight:600;letter-spacing:-.01em}
/* LIVE: the server answers the poll - a green dot that pulses; amber and still once a poll fails */
.page-board .badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 9px 2px 7px;font-weight:700;
  font-size:10px;letter-spacing:.08em;line-height:1.3;color:var(--crew-tone-running);
  background:color-mix(in srgb, var(--crew-tone-running) 12%, transparent)}
.page-board .badge i{width:7px;height:7px;border-radius:50%;background:var(--crew-tone-running);
  animation:livepulse 1.6s ease-out infinite}
@keyframes livepulse{0%{box-shadow:0 0 0 0 var(--crew-running-glow)}70%{box-shadow:0 0 0 6px transparent}
  100%{box-shadow:0 0 0 0 transparent}}
.page-board .badge.stale{color:var(--crew-tone-review);background:color-mix(in srgb, var(--crew-tone-review) 12%, transparent)}
.page-board .badge.stale i{background:var(--crew-tone-review);animation:none}
@media (prefers-reduced-motion: reduce){ .page-board .badge i{animation:none} }
.page-board .meta{font-size:12px;color:var(--crew-text-3);white-space:nowrap}
.page-board .meta.on{color:var(--crew-tone-running)}
.page-board #when{font-size:11px;color:var(--crew-text-4);font-variant-numeric:tabular-nums}
.page-board .stats{display:flex;gap:6px;font-size:11.5px;color:var(--crew-text-3)}
.page-board .stats span{--tone:var(--crew-text-3);display:inline-flex;align-items:baseline;gap:4px;padding:2px 8px;border-radius:5px;
  background:color-mix(in srgb, var(--tone) 12%, transparent);color:var(--tone)}
.page-board .stats b{font-weight:600;font-variant-numeric:tabular-nums}
.page-board .stats .running{--tone:var(--crew-tone-running)}
.page-board .stats .blocked{--tone:var(--crew-tone-blocked)}
.page-board .stats .done{--tone:var(--crew-tone-done)}
.page-board .stats .none{--tone:var(--crew-text-4)}
.page-board .stale{font-size:11px;color:var(--crew-tone-review)}
.page-board .stale[hidden]{display:none}
.page-board .dispatcher-down{margin:0 18px 8px;padding:7px 12px;border-radius:6px;font-size:12.5px;flex:0 0 auto;
  color:var(--crew-tone-blocked);background:color-mix(in srgb, var(--crew-tone-blocked) 12%, transparent)}
.page-board .dispatcher-down code{font:inherit;font-weight:600}
.page-board .hright{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:11px;color:var(--crew-text-4)}
.page-board .hright .node{white-space:nowrap}
.page-board .hright a{color:var(--crew-text-3)}
.page-board .hright a:hover{color:var(--crew-text-1)}
.page-board header{border-bottom:1px solid var(--crew-stroke-2)}
.page-board .avatar{display:inline-grid;place-items:center;flex:0 0 auto;border-radius:999px;width:18px;height:18px;
  font-size:9px;font-weight:600;background:color-mix(in srgb, var(--hue) 22%, transparent);color:var(--hue)}
.page-board .avatar.face{border-radius:6px;object-fit:cover;background:none;padding:0;}
/* a card's state: a chip tinted in its own tone */
.page-board .schip{display:inline-flex;align-items:center;white-space:nowrap;border-radius:4px;padding:1px 6px;font-size:10px;
  font-weight:500;background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone)}
/* lanes */
.page-board main{flex:1;min-height:0;display:flex;gap:10px;padding:12px 18px 16px;overflow-x:auto;align-items:stretch}
.page-board .lane{display:flex;flex-direction:column;flex:1 1 264px;min-width:264px;max-width:340px;border-radius:8px;
  padding:8px;background:var(--crew-fill-3);min-height:0}
.page-board .lane.rail{flex:0 0 32px;min-width:32px;width:32px;align-items:center;gap:6px}
.page-board .lane.rail .lt{writing-mode:vertical-rl;margin-top:4px}
.page-board .lane.rail .ln{margin-top:2px}
.page-board [data-toggle]{cursor:pointer}
.page-board .lane.togglable:hover,.page-board .lane.togglable:focus-visible{background:var(--crew-fill-2,var(--crew-fill-3));outline:none}
.page-board .lh{display:flex;flex:0 0 auto;align-items:center;gap:6px;height:20px;margin:0 4px 6px}
.page-board .lh i{width:6px;height:6px;border-radius:50%;background:var(--tone)}
.page-board .lt{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:var(--crew-text-3)}
.page-board .ln{font-size:10px;color:var(--crew-text-4);font-variant-numeric:tabular-nums}
.page-board .lbody{display:flex;flex-direction:column;gap:8px;overflow-y:auto;min-height:0;padding:1px}
.page-board .more{font-size:11px;color:var(--crew-text-3);text-align:center;padding:6px;border:1px dashed var(--crew-stroke-1);
  border-radius:6px;width:100%}
.page-board .more:hover{color:var(--crew-text-1)}
.page-board .empty{color:var(--crew-text-4);font-size:11px;padding:2px 4px}
/* the card: the Hermes desktop kanban card anatomy */
.page-board .card{position:relative;display:flex;flex-direction:column;gap:8px;border-radius:6px;padding:10px;
  text-decoration:none;color:inherit;background:var(--crew-elevated);border:1px solid var(--crew-stroke-2);
  border-left:2px solid var(--tone)}
.page-board .card:hover{border-color:var(--crew-stroke-1);border-left-color:var(--tone)}
.page-board .card .ti{font-size:13px;font-weight:500;line-height:1.35;color:var(--crew-text-1);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.page-board .card .su{font-size:11px;line-height:1.4;color:var(--crew-text-3);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.page-board .card .ft{display:flex;align-items:center;gap:6px;white-space:nowrap;font-size:10px;color:var(--crew-text-3)}
.page-board .card .ft .who{font-weight:500}
.page-board .card .ft .r{margin-left:auto;display:flex;align-items:center;gap:8px;min-width:0;font-variant-numeric:tabular-nums}
.page-board .card .ft .id{font-family:var(--crew-mono);color:var(--crew-text-4)}
.page-board .ok{color:var(--crew-tone-running)}
.page-board .bad{color:var(--crew-tone-blocked)}
.page-board .warn{color:var(--crew-tone-review)}
.page-board .dim{color:var(--crew-text-4)}
/* motion means work: an arc sweeps the border of a live card; a quiet one crawls amber; reduced motion = ring */
@property --crew-arc{syntax:"<angle>";inherits:false;initial-value:0deg}
.page-board .card.live::after,.page-board .card.quiet::after{content:"";position:absolute;inset:-1px;border-radius:7px;
  padding:1px;pointer-events:none;
  background:conic-gradient(from var(--crew-arc), transparent 0 70%, var(--arc) 88%, transparent 100%);
  -webkit-mask:linear-gradient(currentColor 0 0) content-box,linear-gradient(currentColor 0 0);-webkit-mask-composite:xor;
  mask:linear-gradient(currentColor 0 0) content-box exclude,linear-gradient(currentColor 0 0);
  animation:crewarc var(--arc-s) linear infinite}
.page-board .card.live{--arc:var(--crew-tone-running);--arc-s:2.2s}
.page-board .card.quiet{--arc:var(--crew-tone-review);--arc-s:6s}
@keyframes crewarc{to{--crew-arc:360deg}}
@media (prefers-reduced-motion: reduce){
  .page-board .card.live::after,.page-board .card.quiet::after{animation:none;background:var(--arc)}
}
.page-board #bellwrap{position:relative;display:inline-flex;align-items:center}
.page-board .bell{position:relative;display:inline-flex;align-items:center;gap:6px;background:var(--crew-fill-1);
  color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);border-radius:6px;padding:3px 7px;font:inherit;
  cursor:pointer;line-height:0}
.page-board .bell:hover{border-color:var(--crew-tone-ready)}
.page-board .bell.waiting{border-color:var(--crew-tone-review);color:var(--crew-text-1)}
.page-board .bell .n{background:var(--crew-stroke-1);color:var(--crew-text-3);border-radius:9px;font-weight:700;font-size:10px;
  padding:0 5px;line-height:14px}
.page-board .bell.waiting .n{background:var(--crew-tone-blocked);color:var(--crew-bg)}
.page-board #notes{position:absolute;right:0;top:27px;z-index:40;width:560px;max-width:86vw;max-height:70vh;
  overflow:auto;background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:8px;
  box-shadow:0 10px 28px var(--crew-shadow);padding:8px 9px}
.page-board #notes[hidden]{display:none}
.page-board .nh{display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--crew-text-3);
  font-size:10px;text-transform:uppercase;letter-spacing:.1em;margin:2px 2px 7px}
.page-board .nh b{color:var(--crew-text-1)}
.page-board .nh button,.page-board #noterows button{background:var(--crew-fill-1);color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);
  border-radius:4px;font:inherit;font-size:10px;padding:1px 8px;cursor:pointer}
.page-board .nh button:hover,.page-board #noterows button:hover{border-color:var(--crew-tone-ready)}
.page-board #notes .empty{color:var(--crew-text-4);font-size:11px;padding:2px}
.page-board .ar{display:flex;align-items:center;gap:10px;background:var(--crew-elevated);border:1px solid var(--crew-stroke-1);
  border-left:3px solid var(--crew-tone-neutral);border-radius:6px;padding:5px 9px;margin-bottom:5px;font-size:11px}
.page-board .ar.stuck{border-left-color:var(--crew-tone-blocked)}
.page-board .ar a.t{color:var(--crew-text-1);text-decoration:none;flex:1;min-width:0;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.page-board .ar a.t:hover{color:var(--crew-tone-ready)}
.page-board .ar .st{font-weight:700;width:56px}
.page-board .ar.stuck .st{color:var(--crew-tone-blocked)}
.page-board .ar .st{color:var(--crew-tone-neutral)}
.page-board .ar .w,.page-board .ar .ag{color:var(--crew-text-3);white-space:nowrap}
.page-board .ar button{background:var(--crew-fill-1);color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);border-radius:4px;
  font:inherit;font-size:10px;padding:1px 8px;cursor:pointer}
.page-board .ar button:hover{border-color:var(--crew-tone-ready)}
.page-board .tailnet{color:var(--crew-tone-ready)}

.page-board header a.brand{display:inline-flex;align-items:center;flex:0 0 auto;border-radius:6px}
.page-board header a.brand img{display:block;width:18px;height:18px}
.page-board header a.brand:hover{background:var(--crew-fill-1)}
.page-board header a.brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}

/* narrow (the Desktop main pane beside the flow pane): the title never wraps or vanishes; the header's least
   important facts step aside by width and stay in the DOM */
.page-board header{container-type:inline-size;container-name:crewhead;}
@container crewhead (max-width:900px){
  .page-board header > *{flex-shrink:0;}
  .page-board header > h1{flex-shrink:1;min-width:5.5em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
}
@container crewhead (max-width:900px){ .page-board #when{display:none;} }
@container crewhead (max-width:760px){ .page-board #cards{display:none;} }
@container crewhead (max-width:620px){ .page-board #live{display:none;} }
@container crewhead (max-width:520px){ .page-board .stats .none{display:none;} }

/* Desktop only: the switch that brings the app's own Kanban row back (Board.tsx, host.kanbanRow). */
.page-board .kswitch{display:inline-flex;align-items:center;gap:7px;cursor:pointer;white-space:nowrap;color:var(--crew-text-3)}
.page-board .kswitch:hover{color:var(--crew-text-1)}
.page-board .kswitch input{position:absolute;opacity:0;width:0;height:0}
.page-board .kswitch i{position:relative;width:24px;height:14px;border-radius:7px;background:var(--crew-stroke-1);transition:background .15s}
.page-board .kswitch i::after{content:"";position:absolute;top:2px;left:2px;width:10px;height:10px;border-radius:50%;background:var(--crew-bg);transition:transform .15s}
.page-board .kswitch input:checked + i{background:var(--crew-tone-running)}
.page-board .kswitch input:checked + i::after{transform:translateX(10px)}
.page-board .kswitch input:focus-visible + i{outline:2px solid var(--crew-tone-ready);outline-offset:2px}

/* Desktop only: the command row under a tile's chips (TileActions draws nothing in the browser) */
.page-board .card .tact{display:flex;flex-direction:column;gap:4px;cursor:default}
.page-board .card .tbtns{display:flex;flex-wrap:wrap;align-items:center;gap:4px}
.page-board .card .tmsg{font-size:10px;line-height:1.4;color:var(--crew-text-2);overflow-wrap:anywhere}
.page-board .card .tmsg.bad{color:var(--crew-tone-blocked)}
`;

  // src/components/boardUtil.ts
  function fmt(s) {
    if (s === null || s === void 0) return "";
    s = Math.max(0, Math.floor(s));
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m";
    if (s < 86400) return Math.floor(s / 3600) + "h";
    return Math.floor(s / 86400) + "d";
  }
  var shortId = (id) => String(id).replace(/^t_/, "").slice(0, 6);
  function hhmm(d) {
    const p = (x) => (x < 10 ? "0" : "") + x;
    return p(d.getHours()) + ":" + p(d.getMinutes());
  }
  function store(k, v) {
    try {
      if (v === void 0) return sessionStorage.getItem("crew." + k);
      if (v === null) sessionStorage.removeItem("crew." + k);
      else sessionStorage.setItem("crew." + k, v);
    } catch {
      return null;
    }
  }
  var TONE = {
    blocked: "var(--crew-tone-blocked)",
    triage: "var(--crew-tone-blocked)",
    running: "var(--crew-tone-running)",
    review: "var(--crew-tone-review)",
    ready: "var(--crew-tone-ready)",
    todo: "var(--crew-tone-neutral)",
    done: "var(--crew-tone-done)",
    queued: "var(--crew-tone-ready)",
    other: "var(--crew-tone-neutral)"
  };
  var QUIET_S = 120;

  // src/components/Lane.tsx
  var import_react5 = __toESM(require_react(), 1);

  // src/components/ActionBar.tsx
  var import_react4 = __toESM(require_react(), 1);

  // src/card-format.ts
  function fmtTokens(n) {
    const v = +n || 0;
    if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(1) + "k";
    return "" + v;
  }
  var pad = (x) => (x < 10 ? "0" : "") + x;
  function fmtTime(sec) {
    if (sec == null) return "";
    const d = new Date(sec * 1e3);
    return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
  }
  function fmtAgo(sec) {
    if (!sec) return "";
    let d = Date.now() / 1e3 - sec;
    if (d < 0) d = 0;
    if (d < 60) return Math.round(d) + "s ago";
    if (d < 3600) return Math.round(d / 60) + "m ago";
    if (d < 86400) return Math.round(d / 3600) + "h ago";
    return Math.round(d / 86400) + "d ago";
  }
  function fmtAge(sec) {
    if (sec === null || sec === void 0 || sec === "") return "age unknown";
    const s = Math.max(0, Math.round(+sec || 0));
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.floor(s / 60) + "m " + s % 60 + "s ago";
    if (s < 86400) return Math.floor(s / 3600) + "h " + Math.floor(s % 3600 / 60) + "m ago";
    return Math.floor(s / 86400) + "d " + Math.floor(s % 86400 / 3600) + "h ago";
  }
  function fmtExact(n) {
    return Math.round(+n || 0).toLocaleString("en-US");
  }
  function offLabel(s) {
    return s.sec != null ? "t+" + s.sec + "s" : "";
  }
  function cap1(s) {
    const t = String(s || "");
    return t.charAt(0).toUpperCase() + t.slice(1);
  }
  function hhmm2(ts) {
    return ts ? fmtTime(ts).slice(0, 5) : "";
  }
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function dayTime(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1e3);
    return MONTHS[d.getMonth()] + " " + d.getDate() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  var ROLE_ICON = { coordinator: "\u25C6", worker: "\u25B2", content: "\u25CF", verifier: "\u2713" };
  var roleIcon = (name) => ROLE_ICON[name || ""] || "\u25AA";
  var STATUS_TONE = {
    running: "running",
    live: "running",
    pending: "neutral",
    done: "done",
    completed: "done",
    finished: "done",
    blocked: "blocked",
    triage: "blocked",
    failed: "blocked",
    crashed: "blocked",
    timed_out: "blocked",
    gave_up: "blocked",
    review: "review",
    review_requested: "review",
    ready: "ready",
    queued: "ready",
    todo: "neutral",
    PASS: "running",
    verified: "running",
    FAIL: "blocked",
    unverified: "review",
    rate_limited: "review"
  };
  var toneVar = (word) => "var(--crew-tone-" + (STATUS_TONE[word || ""] || "neutral") + ")";
  function budgetTone(pct) {
    const G = "var(--crew-tone-running)", Y = "var(--crew-tone-review)", R = "var(--crew-tone-blocked)";
    if (pct >= 100) return R;
    if (pct >= 80) return "color-mix(in srgb, " + R + " " + Math.round((pct - 80) / 20 * 100) + "%, " + Y + ")";
    if (pct >= 50) return "color-mix(in srgb, " + Y + " " + Math.round((pct - 50) / 30 * 100) + "%, " + G + ")";
    return G;
  }
  var stepWord = (s) => s.state === "err" ? "failed" : s.state === "pending" ? "still running" : "ok";
  function groupParallel(steps) {
    const out = [];
    for (const s of steps || []) {
      const k = (s.tool || "?") + "@" + (s.ts || 0);
      const last = out[out.length - 1];
      if (last && last.k === k) {
        last.args.push(s.args || "");
        last.states.push(s.state);
        if (!last.note) last.note = s.note;
        if (s.out) last.out = s.out;
        if (!last.say) last.say = s.say;
      } else {
        out.push({ k, tool: s.tool, ts: s.ts, sec: s.sec, args: [s.args || ""], states: [s.state], note: s.note, out: s.out, say: s.say, state: "" });
      }
    }
    for (const g of out) g.state = g.states.indexOf("err") >= 0 ? "err" : g.states.indexOf("pending") >= 0 ? "pending" : "ok";
    return out;
  }
  function stepStatus(g) {
    const note = g.note || "", out = g.out || "";
    let text = "";
    if (note && out) text = out.indexOf(note) === 0 || note.indexOf(out) === 0 ? out.length > note.length ? out : note : note + " - " + out;
    else text = note || out;
    const bits = [stepWord(g)];
    if (text) bits.push(text);
    if (g.ts) bits.push(fmtTime(g.ts));
    return bits.join(" - ");
  }
  var tickTime = (s) => s.ts ? fmtTime(s.ts) : offLabel(s);
  function coordinatorTarget(value) {
    const m = /^([^/]*)\/([^/]*)$/.exec(String(value || ""));
    if (!m || m[2] === "no-session") return null;
    if (!/^[A-Za-z0-9_.-]{1,64}$/.test(m[1]) || !/^[A-Za-z0-9_-]{1,128}$/.test(m[2])) return null;
    return { profile: m[1], session: m[2] };
  }
  function copyText(text, done2) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => done2(true), () => done2(false));
        return;
      }
    } catch {
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-1000px";
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, ta.value.length);
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      done2(ok);
    } catch {
      done2(false);
    }
  }
  function briefFields(nodes) {
    const b = nodes.find((n) => n.kind === "brief")?.brief || null;
    if (!b || !String(b.text || "").trim()) return null;
    const src = b.source || "owner";
    const when = b.ts ? fmtTime(b.ts) : "";
    const label = src === "owner" ? "the owner's words when /crew was called" : src === "card goal" ? "the card's own GOAL line - no brief was recorded" : "source: " + src;
    return { text: String(b.text).trim(), src: label + (when ? " - " + when : "") };
  }

  // src/components/ActionBar.tsx
  var import_jsx_runtime = __toESM(require_jsx_runtime(), 1);
  var cardSubject = (card) => ({
    status: card.card_status || "",
    proof_ask: card.situation?.proof_ask || "",
    live: !!card.situation?.live_run
  });
  function actionStates(s) {
    const st = s.status;
    return {
      unstuck: st === "triage" || st === "blocked" || st === "scheduled",
      retry: st === "done" || st === "blocked" || st === "failed" || st === "triage",
      proof: !!s.proof_ask,
      stop: s.live
    };
  }
  var WHY_NOT = {
    unstuck: "only a blocked, triage or stopped card can be unstuck",
    retry: "only a done, blocked or failed card can be retried",
    proof: "no proof question is waiting for you on this card",
    stop: "no run is alive on this card"
  };
  var WHAT = {
    unstuck: "lift the block so the card runs again (/crew-unstuck)",
    retry: "raise the budget and run the card again",
    proof: "give the go for the proof the coordinator asked about (/crew-proof)",
    stop: "park the card and stop its run (/crew-stop)"
  };
  var LABEL = { unstuck: "Unstuck", retry: "Retry", proof: "Proof", stop: "Stop" };
  var SHOW_MS = 6e3;
  var NAMES = ["unstuck", "retry", "proof", "stop"];
  function ActionButtons({ subject, card, compact, only, onResult, onDone }) {
    const { actions } = useCrewHost();
    const [busy, setBusy] = (0, import_react4.useState)(null);
    if (!actions) return null;
    const { Button } = actions;
    const on = actionStates(subject);
    const press = async (name) => {
      if (busy || !on[name]) return;
      const extra = {};
      if (name === "stop") {
        if (!await actions.confirm("Stop this card?", "Its run is killed and the card is parked with its history. /crew-unstuck continues it.")) return;
        extra.confirm = true;
      }
      if (name === "proof") {
        const brave = subject.proof_ask !== "rescope";
        if (brave && !await actions.confirm("Run the flagged proof?", "Hermes flagged this proof command as dangerous. Brave runs it for this card anyway.")) return;
        extra.mode = brave ? "brave" : "yes";
      }
      setBusy(name);
      try {
        onResult(await actions.run(name, card, extra));
      } catch (e) {
        onResult({ ok: false, text: LABEL[name] + " failed: " + (e instanceof Error ? e.message : String(e)) });
      }
      setBusy(null);
      onDone();
    };
    return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(import_jsx_runtime.Fragment, { children: NAMES.filter((n) => (!only || only.includes(n)) && (n !== "proof" || on.proof)).map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
      Button,
      {
        id: compact ? void 0 : "act-" + n,
        size: "xs",
        variant: n === "stop" ? "destructive" : n === "proof" ? "default" : "outline",
        disabled: !on[n] || !!busy,
        title: on[n] ? WHAT[n] : WHY_NOT[n],
        onClick: () => {
          void press(n);
        },
        children: LABEL[n]
      },
      n
    )) });
  }
  function useFlash(reset) {
    const [msg, setMsg] = (0, import_react4.useState)(null);
    const timer = (0, import_react4.useRef)(null);
    (0, import_react4.useEffect)(() => () => {
      if (timer.current) clearTimeout(timer.current);
    }, []);
    (0, import_react4.useEffect)(() => {
      setMsg(null);
    }, [reset]);
    return [msg, (m) => {
      setMsg(m);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setMsg(null), SHOW_MS);
    }];
  }
  function ActionBar({ card, openChat, onDone }) {
    const { actions } = useCrewHost();
    const [msg, show] = useFlash(card.card_id);
    if (!actions) return null;
    const { Button } = actions;
    const target = coordinatorTarget(card.coordinator);
    return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { id: "actionbar", className: "actionbar", children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: "abtns", children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActionButtons, { subject: cardSubject(card), card: card.card_id, onResult: show, onDone }),
        target && openChat ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
          Button,
          {
            id: "act-chat",
            size: "xs",
            variant: "ghost",
            title: "open the chat this card came from",
            onClick: () => openChat(target.profile, target.session),
            children: "Open chat"
          }
        ) : null
      ] }),
      msg ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { id: "actionmsg", role: "status", className: "amsg" + (msg.ok ? "" : " bad"), children: msg.text }) : null
    ] });
  }
  function TileActions({ t, lane }) {
    const { actions } = useCrewHost();
    const [msg, show] = useFlash(t.id);
    if (!actions || lane !== "blocked") return null;
    const subject = { status: t.status, proof_ask: t.proof_ask || "", live: !!t.active };
    return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: "tact", onClick: (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "tbtns", children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActionButtons, { compact: true, only: ["unstuck", "retry", "proof"], subject, card: t.id, onResult: show, onDone: () => {
      } }) }),
      msg ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { role: "status", className: "tmsg" + (msg.ok ? "" : " bad"), children: msg.text }) : null
    ] });
  }

  // src/components/CardTile.tsx
  var import_jsx_runtime2 = __toESM(require_jsx_runtime(), 1);
  var tone = (v) => ({ "--tone": v });
  function Chip({ text, kind }) {
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { className: "schip", style: tone("var(--crew-tone-" + kind + ")"), children: text });
  }
  function State({ t }) {
    const a = t.active;
    if (a) {
      if (a.quiet_s !== null && a.quiet_s !== void 0 && a.quiet_s > QUIET_S) return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "no heartbeat", kind: "review" });
      let facts = "";
      if (a.steps) facts += " \xB7 step " + (+a.steps || 0);
      if (a.last_tool) facts += " \xB7 last: " + a.last_tool;
      return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "working \xB7 " + fmt(+a.for_s) + facts, kind: "running" });
    }
    if (t.status === "ready" || t.status === "todo") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "queued", kind: "ready" });
    if (t.status === "blocked" || t.status === "triage") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: t.status === "triage" ? "needs you" : "blocked", kind: "blocked" });
    if (t.status === "review") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "in review", kind: "review" });
    if (t.status !== "done") return null;
    if (t.verdict === "PASS") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "\u2713 verified", kind: "running" });
    if (t.verdict === "FAIL") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "\u2715 verify failed", kind: "blocked" });
    if (t.verdict === "unverified") return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "\u25CB unverified", kind: "review" });
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Chip, { text: "done", kind: "done" });
  }
  function Avatar({ api, name, hue }) {
    const src = useAvatar(api, name);
    if (name) return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("img", { className: "avatar face", src, alt: name, title: name });
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { className: "avatar", style: { "--hue": hue || "var(--crew-text-3)" }, children: "?" });
  }
  function CardTile({ t, lane, api, onOpen }) {
    const who = t.active ? t.active.profile : t.role || t.assignee || "unassigned";
    const b = t.budget;
    const quiet = !!t.active && t.active.quiet_s !== null && t.active.quiet_s !== void 0 && t.active.quiet_s > QUIET_S;
    const motion = t.active ? quiet ? " quiet" : " live" : "";
    const open = (e) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      onOpen(t.id);
    };
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("a", { className: "card" + motion, "data-id": t.id, href: "/card/" + t.id, style: tone(TONE[t.status] || "var(--crew-tone-neutral)"), onClick: open, children: [
      /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { className: "ti", children: t.title || "(untitled)" }),
      t.summary ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("div", { className: "su", children: t.summary }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { className: "ft", children: [
        /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(Avatar, { api, name: who === "unassigned" ? "" : who, hue: t.color }),
        /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { className: "who", children: who }),
        /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(State, { t }),
        /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("span", { className: "r", children: [
          t.runs !== void 0 && t.runs > 1 ? /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("span", { title: "runs", children: [
            "\u21BB ",
            +t.runs || 0
          ] }) : null,
          b && b.pct >= 80 ? /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("span", { className: b.pct >= 100 ? "bad" : "warn", title: "token budget: " + (+b.used || 0) + " of " + (+b.ceiling || 0), children: [
            Math.round(b.pct),
            "%"
          ] }) : null,
          /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { title: "time in this state", children: fmt(t.settled_s !== null && t.settled_s !== void 0 ? t.settled_s : t.age_s) }),
          /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { className: "id", title: t.id, children: shortId(t.id) })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(TileActions, { t, lane })
    ] });
  }

  // src/components/Lane.tsx
  var import_jsx_runtime3 = __toESM(require_jsx_runtime(), 1);
  function LaneBody({ laneKey, children }) {
    const ref = (0, import_react5.useRef)(null);
    (0, import_react5.useLayoutEffect)(() => {
      const y = +(store("scroll." + laneKey) || 0);
      if (y && ref.current) ref.current.scrollTop = y;
    }, [laneKey]);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "lbody", ref, onScroll: (e) => store("scroll." + laneKey, String(e.currentTarget.scrollTop)), children });
  }
  function Lane({ lane: l, api, archivedOpen, older, onToggleArchived, onOlder, onOpenCard }) {
    const tone4 = { "--tone": TONE[l.key] || "var(--crew-tone-neutral)" };
    const n = l.tiles.length + (l.hidden || 0);
    const key = (fn) => (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      fn();
    };
    if (l.key === "archived" && n && !archivedOpen)
      return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
        "section",
        {
          className: "lane rail togglable",
          "data-lane": "archived",
          "data-toggle": "archived",
          role: "button",
          tabIndex: 0,
          "aria-expanded": "false",
          style: tone4,
          title: "Archived: " + n + " - click to open",
          onClick: onToggleArchived,
          onKeyDown: key(onToggleArchived),
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "lh", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("i", {}) }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "lt", children: l.label }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "ln", children: n })
          ]
        }
      );
    if (!n)
      return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "lane rail", "data-lane": l.key, style: tone4, title: l.label + ": empty", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "lh", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("i", {}) }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "lt", children: l.label })
      ] });
    const toggle = l.key === "archived";
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "lane", "data-lane": l.key, style: tone4, children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
        "div",
        {
          className: "lh",
          ...toggle ? { "data-toggle": "archived", role: "button", tabIndex: 0, "aria-expanded": "true", title: "click to collapse", onClick: onToggleArchived, onKeyDown: key(onToggleArchived) } : {},
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("i", {}),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "lt", children: l.label }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "ln", children: n })
          ]
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(LaneBody, { laneKey: l.key, children: [
        l.tiles.map((t) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(CardTile, { t, lane: l.key, api, onOpen: onOpenCard }, t.id)),
        l.hidden && l.key === "done" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("button", { className: "more", "data-older": "1", onClick: () => onOlder(true), children: [
          "Show ",
          +l.hidden || 0,
          " older"
        ] }) : l.key === "done" && older ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("button", { className: "more", "data-older": "0", onClick: () => onOlder(false), children: "Show the newest only" }) : null
      ] })
    ] });
  }

  // src/components/Board.tsx
  var import_jsx_runtime4 = __toESM(require_jsx_runtime(), 1);
  var HEADER = [["running", "running", ["running"]], ["blocked", "blocked", ["blocked", "triage"]], ["done", "done", ["done"]]];
  var BELL = /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("svg", { width: "15", height: "15", viewBox: "0 0 24 24", "aria-hidden": "true", fill: "currentColor", children: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("path", { d: "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" }) });
  function Board({ api, onOpenCard, flags, onFlags, home }) {
    injectCss("base", base_default);
    injectCss("board", board_default);
    const { kanbanRow } = useCrewHost();
    const all = flags?.all ?? (typeof location !== "undefined" && /[?&]all=1/.test(location.search));
    const [older, setOlder] = (0, import_react6.useState)(() => flags?.older ?? !!store("older"));
    (0, import_react6.useEffect)(() => {
      if (flags?.older !== void 0) setOlder(flags.older);
    }, [flags?.older]);
    const [archivedOpen, setArchivedOpen] = (0, import_react6.useState)(() => {
      if (typeof location !== "undefined" && location.hash === "#archived") store("archived.open", "1");
      return !!store("archived.open");
    });
    const query = [all ? "all=1" : "", older ? "older=1" : ""].filter(Boolean).join("&");
    const { board, error, loading, refresh } = useBoard(api, 2e3, query);
    const setOlderFlag = (on) => {
      store("older", on ? "1" : null);
      setOlder(on);
      onFlags?.({ all, older: on });
    };
    const toggleArchived = () => {
      const next = !archivedOpen;
      store("archived.open", next ? "1" : null);
      setArchivedOpen(next);
    };
    const [staleSince, setStaleSince] = (0, import_react6.useState)(null);
    (0, import_react6.useEffect)(() => {
      setStaleSince((s) => error ? s || /* @__PURE__ */ new Date() : null);
    }, [error]);
    const when = (0, import_react6.useMemo)(() => board ? (/* @__PURE__ */ new Date()).toLocaleTimeString() : "", [board]);
    const [cleared, setCleared] = (0, import_react6.useState)(/* @__PURE__ */ new Set());
    (0, import_react6.useEffect)(() => {
      setCleared(/* @__PURE__ */ new Set());
    }, [board]);
    const [notesOpen, setNotesOpen] = (0, import_react6.useState)(false);
    const wrap = (0, import_react6.useRef)(null);
    (0, import_react6.useEffect)(() => {
      const away = (e) => {
        if (!wrap.current?.contains(e.target)) setNotesOpen(false);
      };
      const esc = (e) => {
        if (e.key === "Escape" && isCrewKey(e, wrap.current?.closest(".crew-scope") || null)) setNotesOpen(false);
      };
      document.addEventListener("click", away);
      document.addEventListener("keydown", esc);
      return () => {
        document.removeEventListener("click", away);
        document.removeEventListener("keydown", esc);
      };
    }, []);
    const ack = (path, ids) => {
      setCleared((c) => /* @__PURE__ */ new Set([...c, ...ids]));
      api.post(path).then(refresh, refresh);
    };
    if (!board) {
      const box = { padding: 16, fontFamily: "var(--crew-font)" };
      return /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("div", { style: box, children: error ? "Crew could not load: " + error : loading ? "Loading..." : "" });
    }
    const att = board.attention || {};
    const rows = (att.rows || []).filter((r) => !cleared.has(r.id));
    const live = board.live || 0;
    const cards = board.cards || 0;
    const counts = board.counts || {};
    const link = (board.dashboard_url || (typeof location !== "undefined" ? location.origin : "")) + "/";
    const brand = /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("a", { className: "brand", href: "/", title: "overview", "aria-label": "crew overview", onClick: home ? (e) => {
      e.preventDefault();
      home();
    } : void 0, children: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("img", { src: MARK_URI, alt: "", width: 26, height: 26 }) });
    return /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { className: "page-board crew-scope", children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("header", { children: [
        brand,
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { className: "badge" + (error ? " stale" : ""), id: "badge", title: error ? "the board server is not answering" : "the board server answers", children: [
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("i", {}),
          "LIVE"
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("h1", { children: "crew board" }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "meta", id: "cards", children: cards + " card" + (cards === 1 ? "" : "s") }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "meta" + (live ? " on" : ""), id: "live", children: live ? live + " working now" : "nothing running" }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("div", { className: "stats", id: "counts", children: HEADER.map(([cls, word, statuses]) => {
          const n = statuses.reduce((a, s) => a + (counts[s] || 0), 0);
          return /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { className: cls + (n ? "" : " none"), children: [
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("b", { children: n }),
            word
          ] }, cls);
        }) }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "meta", id: "when", children: "updated " + when }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "stale", id: "stale", hidden: !error, children: staleSince ? "stale since " + hhmm(staleSince) : "" }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { className: "hright", children: [
          kanbanRow ? /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("label", { className: "kswitch", title: "Hermes shows its own Kanban row in the sidebar; Crew hides it unless this is on", children: [
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("input", { type: "checkbox", role: "switch", checked: kanbanRow.show, onChange: (e) => kanbanRow.set(e.target.checked) }),
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("i", { "aria-hidden": "true" }),
            "Show Hermes Kanban row"
          ] }) : null,
          /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { id: "bellwrap", ref: wrap, children: [
            /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(
              "button",
              {
                id: "bell",
                className: "bell" + (rows.length ? " waiting" : ""),
                "aria-label": "notifications",
                title: rows.length ? rows.length + " waiting - click for the list" : "nothing waiting",
                onClick: () => setNotesOpen((o) => !o),
                children: [
                  BELL,
                  /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "n", id: "belln", children: rows.length })
                ]
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { id: "notes", hidden: !notesOpen, children: [
              /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { className: "nh", children: [
                /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { id: "notehead", children: [
                  "needs you - ",
                  /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("b", { children: +(att.stuck || 0) }),
                  " stuck - ",
                  /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("b", { children: +(att.done || 0) }),
                  " done"
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("button", { id: "clearall", title: "clear every listed row", onClick: () => ack("/ack/all", rows.map((r) => r.id)), children: "clear all" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("div", { id: "noterows", children: rows.length ? rows.map((r) => /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { className: "ar" + (r.status !== "done" ? " stuck" : ""), children: [
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "st", children: r.status }),
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("a", { className: "t", href: "/card/" + r.id, onClick: (e) => {
                  e.preventDefault();
                  setNotesOpen(false);
                  onOpenCard(r.id);
                }, children: r.id + " - " + (r.title || "(untitled)") }),
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "w", children: r.who || "-" }),
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "ag", children: fmt(+r.age_s) }),
                /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("button", { title: "clear this one", onClick: () => ack("/ack/" + r.id, [r.id]), children: "\u2715" })
              ] }, r.id)) : /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("div", { className: "empty", children: "nothing waiting" }) })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("span", { className: "node", children: [
            (board.node || "") + " - kanban" + (board.board && board.board !== "default" ? " " + board.board : "") + " ",
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("a", { className: "tailnet", href: link, children: "link" })
          ] })
        ] })
      ] }),
      board.dispatcher && board.dispatcher.alive === false ? /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { className: "dispatcher-down", id: "dispatcher-down", role: "alert", children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("b", { children: "Cards will not start." }),
        " " + (board.dispatcher.detail || "The gateway is not running") + ". Start it with ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: board.dispatcher.command || "hermes gateway run" })
      ] }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("main", { id: "board", children: board.lanes.map((l) => /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(
        Lane,
        {
          lane: l,
          api,
          archivedOpen,
          older,
          onToggleArchived: toggleArchived,
          onOlder: setOlderFlag,
          onOpenCard
        },
        l.key
      )) })
    ] });
  }

  // src/components/CardPage.tsx
  var import_react12 = __toESM(require_react(), 1);

  // src/card-ui.ts
  var import_react7 = __toESM(require_react(), 1);
  var CardUiContext = (0, import_react7.createContext)(null);
  function useCardUi() {
    const ui = (0, import_react7.useContext)(CardUiContext);
    if (!ui) throw new Error("useCardUi: no CardPage above");
    return ui;
  }

  // src/styles/card.css
  var card_default = `/* The card page, ported from scripts/crew_dashboard/crew.css (everything except the flow graph and minimap, which
   graph.css carries). Scoped under .page-card, which is now the page's root element instead of <body>. */
/* The reset skips the Desktop button bar (:where keeps the selector's weight at one class): its Buttons are the app's own,
   styled by utilities in a CSS layer, and an unlayered padding:0 here would strip every one of them. */
.page-card *:where(:not(#actionbar *)){box-sizing:border-box;margin:0;padding:0;}
/* the page root (it was <body>): fills its host. The served page keeps the browser's own 8px body margin, so the
   screenshots match the old page; Desktop's host has no such margin. */
.page-card{height:100%;flex:0 0 auto;min-width:0;}
#crew-app > .page-card{margin:8px;height:calc(100% - 16px);}
/* body.page-card became .page-card */
.page-card{display:flex;flex-direction:column;background:var(--crew-bg);color:var(--crew-text-2);
  font:12px/1.5 var(--crew-font);overflow:hidden;}
.page-card #event{flex:0 0 auto;padding:6px 14px;border-bottom:1px solid var(--crew-stroke-1);
  display:flex;align-items:center;gap:12px;white-space:nowrap;overflow:hidden;font-size:12px;}
.page-card #event .evmain{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;}
.page-card #event .t{color:var(--crew-text-3);margin-right:8px;}
.page-card #event .txt{color:var(--crew-text-1);}
.page-card #main{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}
.page-card #row{flex:1 1 auto;display:flex;min-height:0;}
.page-card #rail{flex:0 0 212px;border-right:1px solid var(--crew-stroke-2);background:var(--crew-elevated);
  padding:10px 9px;display:flex;flex-direction:column;min-height:0;overflow-y:auto;}
.page-card #toksec{flex:0 0 auto;border:1px solid var(--crew-stroke-1);border-radius:5px;background:var(--crew-bg);
  padding:6px 8px;margin-bottom:10px;}
.page-card #toksec .tokrow{display:flex;align-items:baseline;gap:8px;font-size:11px;line-height:1.6;}
.page-card #toksec .tk{color:var(--crew-text-3);}
.page-card #toksec .tv{margin-left:auto;color:var(--crew-text-1);transition:color .3s;font-variant-numeric:tabular-nums;white-space:nowrap;}
.page-card #rail.collapsed #toksec{display:none;}
.page-card #rail.collapsed{flex:0 0 44px;padding:10px 6px;overflow:hidden;}
.page-card #rail.collapsed .rbtnlabel,.page-card #rail.collapsed #briefsec{display:none;}
@keyframes ldot{0%,100%{box-shadow:0 0 0 0 transparent;transform:scale(1);}
  50%{box-shadow:0 0 0 4px var(--crew-running-halo);transform:scale(1.25);}}
.page-card #toparea{flex:0 0 auto;display:grid;width:100%;max-width:100%;
  grid-template-columns:minmax(0,1.15fr) minmax(0,1fr) minmax(0,1fr);gap:8px;padding:6px 12px;
  align-items:stretch;border-bottom:1px solid var(--crew-stroke-1);background:var(--crew-bg);
  max-height:40vh;overflow-y:auto;overflow-x:hidden;}
/* A card that is not looping has nothing to say in the third column, so its cell goes and the two
   live boxes take the width: the reason box stops wrapping into a fourth line and the card box
   keeps its fields on one line. Two tracks, not three with a note in one. */
.page-card #toparea.two{grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);}
/* \u2500\u2500 the card page's top area: the same design language as the step panel (ui-spec sections 3 and 5) \u2500\u2500
   each cell is a quiet elevated box with a small-caps label; state is a tinted pill in its tone; the run
   counts are a key-number grid; the card's own ids are copy chips; the reason boxes are callouts. */
.page-card #toparea .tcell{min-width:0;display:flex;flex-direction:column;gap:6px;padding:7px 10px;
  border:1px solid var(--crew-stroke-2);border-radius:8px;background:var(--crew-elevated);overflow-x:hidden;}
/* .tcell sets display:flex, which would beat the user agent's [hidden] rule: say it here. */
.page-card #toparea .tcell[hidden]{display:none;}
.page-card #toparea .tcell > .tch{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);}
.page-card #toparea .tcell > .tce{color:var(--crew-text-3);font-size:12px;}
.page-card #toparea .tcell > .tce[hidden]{display:none;}
@media (max-width:760px){
  .page-card #toparea{grid-template-columns:minmax(0,1fr);max-height:55vh;}
  .page-card #toparea.two{grid-template-columns:minmax(0,1fr);}
}
/* a state chip anywhere on the card page: tinted in its own tone (set --tone on the element) */
.page-card .chip-tone,.page-card #sit .pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:4px;
  padding:2px 8px;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #sit .pill i{width:6px;height:6px;border-radius:50%;background:var(--tone);}
.page-card #sit{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0;max-width:100%;font-size:12px;}
.page-card #sit > *{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:break-word;}
/* the run counts: one compact strip at the right end of the top event line - "3 runs | 1 done | 2 blocked ..." */
.page-card .sitkpis{display:inline-flex;align-items:stretch;border:1px solid var(--crew-stroke-2);border-radius:5px;
  background:var(--crew-bg);margin-left:auto;flex:0 0 auto;}
.page-card .sitkpis .kpi{display:flex;align-items:baseline;gap:4px;padding:1px 8px;border-left:1px solid var(--crew-stroke-2);}
.page-card .sitkpis .kpi:first-child{border-left:0;}
.page-card .sitkpis .kv{font-size:12px;font-weight:600;color:var(--crew-text-1);font-variant-numeric:tabular-nums;}
.page-card .sitkpis .kv.on{color:var(--tone);}
.page-card .sitkpis .kl{font-size:10px;color:var(--crew-text-4);}
/* The card's own fields: copy chips, the way the panel shows ids - label, mono value, copy */
.page-card #sitfields{display:flex;flex-wrap:wrap;align-items:center;gap:4px 5px;min-width:0;max-width:100%;}
.page-card #sitfields[hidden]{display:none;}
.page-card #sitfields .fp{display:inline-flex;align-items:baseline;gap:5px;font-size:10.5px;min-width:0;max-width:100%;
  border:1px solid var(--crew-stroke-2);border-radius:5px;padding:0 4px 0 7px;line-height:16px;}
.page-card #sitfields .fk{flex:0 0 auto;color:var(--crew-text-3);}
.page-card #sitfields .fv{min-width:0;max-width:34ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-family:var(--crew-mono);color:var(--crew-text-2);}
.page-card #sitfields .fp.act .fv{color:var(--crew-tone-running);}
.page-card #sitfields .copy{flex:0 0 auto;background:none;color:var(--crew-text-4);border:0;border-left:1px solid var(--crew-stroke-2);
  font:inherit;font-size:10px;line-height:14px;padding:0 0 0 5px;cursor:pointer;}
.page-card #sitfields .copy:hover{color:var(--crew-text-1);}
.page-card #sitfields .copy:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:1px;}
/* The open chat button sits on a row of its own, in the copy buttons' quiet style, with no divider before it. */
.page-card #sitfields .brk{flex-basis:100%;height:0;}
.page-card #sitfields .openrow .copy{border-left:0;padding-left:0;}
/* Desktop only: the commands for this card, under its fields (ActionBar draws nothing in the browser) */
.page-card #actionbar{display:flex;flex-direction:column;gap:4px;margin-top:2px;}
.page-card #actionbar .abtns{display:flex;flex-wrap:wrap;align-items:center;gap:5px;}
.page-card #actionbar .amsg{font-size:11px;line-height:1.4;color:var(--crew-text-2);overflow-wrap:anywhere;}
.page-card #actionbar .amsg.bad{color:var(--crew-tone-blocked);}
/* the pending reason and the repeated-stop note: callouts in their tone */
.page-card #sitbox,.page-card #spinbox{--tone:var(--crew-tone-blocked);margin:0;border:1px solid color-mix(in srgb, var(--tone) 22%, transparent);
  border-left:2px solid var(--tone);border-radius:6px;background:color-mix(in srgb, var(--tone) 7%, transparent);
  font-size:12px;overflow-y:auto;overflow-x:hidden;flex:0 0 auto;}
.page-card #sitbox{max-height:none;overflow:visible;}
/* only the text scrolls: the head and its copy button stay put */
.page-card #sitboxWhy{max-height:calc(2.9em + 7px);overflow-y:auto;}
/* 2 lines, so the top area keeps its height */
.page-card #spinbox{--tone:var(--crew-tone-review);max-height:28vh;}
.page-card #sitbox[hidden],.page-card #spinbox[hidden]{display:none;}
.page-card #sitbox.nobody{--tone:var(--crew-tone-review);}
.page-card #sitbox.done{--tone:var(--crew-tone-done);}
.page-card #sitboxHead,.page-card #spinboxHead{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:5px 9px 0;}
.page-card #sitboxHead .sbl{font-size:12px;font-weight:500;color:var(--tone);}
.page-card #sitboxHead .sb{--tone:var(--crew-tone-neutral);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  padding:1px 7px;border-radius:4px;background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #sitboxHead .sb.blocked,.page-card #sitboxHead .sb.failed{--tone:var(--crew-tone-blocked);}
.page-card #sitboxHead .sb.running{--tone:var(--crew-tone-running);}
.page-card #sitboxHead .sb.done{--tone:var(--crew-tone-done);}
.page-card #sitboxWhy,.page-card #spinboxText{padding:3px 9px 4px;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
  color:var(--crew-text-1);font-size:12px;line-height:1.45;}
.page-card #sitboxMeta{padding:0 9px 5px;color:var(--crew-text-3);font-size:10px;}
.page-card #spinboxCount{font-size:12px;font-weight:500;color:var(--tone);}
.page-card #spinboxHead .sbl{font-size:10px;font-weight:600;padding:1px 7px;border-radius:4px;color:var(--tone);
  background:color-mix(in srgb, var(--tone) 15%, transparent);text-transform:uppercase;letter-spacing:.04em;}
.page-card #sitCopy,.page-card #spinCopy{margin-left:auto;font:inherit;font-size:10.5px;padding:1px 7px;border-radius:4px;cursor:pointer;
  border:1px solid var(--crew-stroke-1);background:transparent;color:var(--crew-text-3);}
.page-card #sitCopy:hover,.page-card #spinCopy:hover{color:var(--crew-text-1);border-color:var(--crew-text-3);}
.page-card #spinboxText{padding:8px 10px;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
  color:var(--crew-text-2);line-height:1.45;}
.page-card #briefsec{padding:8px 10px 10px;border-bottom:1px solid var(--crew-stroke-1);}
.page-card #briefText{white-space:pre-wrap;word-break:break-word;font-size:10px;line-height:1.5;color:var(--crew-text-2);max-height:180px;overflow:auto;}
.page-card #briefSrc{color:var(--crew-text-3);font-size:9px;margin-top:4px;}
/* A session-text line that just arrived: animated once, on arrival only (the panel keeps a
   per-node key cache so the 2 s poll never replays it). stepIn is a chip animation - its
   max-height:16px would clip a wrapped line - so a text line gets its own. */
@keyframes sayIn{from{opacity:0;transform:translateY(-6px);}to{opacity:1;transform:translateY(0);}}
.page-card #scrubwrap{flex:0 0 auto;border-top:1px solid var(--crew-stroke-1);padding:8px 14px 4px;}
.page-card #scrubber{position:relative;height:34px;}
.page-card #scrubber .track{position:absolute;top:5px;left:0;right:0;border-top:1px solid var(--crew-stroke-1);}
.page-card #scrubber .tl{position:absolute;top:15px;font-size:9px;color:var(--crew-text-3);white-space:nowrap;}
.page-card #scrubber .tl.left{left:0;}
.page-card #scrubber .tl.right{right:0;}
.page-card #scrubber .tick{position:absolute;top:1px;transform:translateX(-50%);cursor:pointer;}
.page-card #scrubber .diam{width:8px;height:8px;border:1px solid var(--crew-text-3);background:transparent;transform:rotate(45deg);}
.page-card #scrubber .tick.active .diam{border-color:var(--crew-text-1);}
.page-card #scrubber .tick.playhead .diam{border-color:var(--crew-text-1);background:var(--crew-text-1);}
.page-card #statusbar{flex:0 0 auto;display:flex;align-items:center;gap:10px;padding:7px 14px 11px;
  border-top:1px solid var(--crew-stroke-1);background:var(--crew-elevated);font-size:11px;}
.page-card .pill{background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:10px;padding:1px 8px;color:var(--crew-text-2);}
.page-card .pill.btn{cursor:pointer;}
.page-card .pill.on{border-color:var(--crew-tone-running);color:var(--crew-tone-running);}
.page-card .live{background:var(--crew-tone-running);color:var(--crew-bg);border-radius:4px;padding:1px 8px;font-weight:700;
  font-size:10px;letter-spacing:.5px;}
.page-card .live.paused{background:var(--crew-text-3);}
.page-card #cardtitle{color:var(--crew-text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:30%;}
.page-card #statusbar .meta{margin-left:auto;display:flex;align-items:center;gap:14px;color:var(--crew-text-3);}
.page-card #statusbar .meta a{color:var(--crew-tone-ready);text-decoration:none;}
.page-card #statusbar .meta a:hover{text-decoration:underline;}
.page-card .hints{font-size:10px;}
.page-card #help{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--crew-elevated);
  border:1px solid var(--crew-stroke-1);border-radius:8px;padding:16px 20px;z-index:60;display:none;
  font-size:12px;box-shadow:0 10px 30px var(--crew-shadow);}
.page-card #help.open{display:block;}
.page-card #help .h{font-weight:700;margin-bottom:8px;}
.page-card #help .row{margin:3px 0;}
.page-card #help kbd{background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:3px;padding:0 5px;margin-right:6px;}
/* \u2500\u2500 step panel (ui-spec section 5): the third column of #row, below the top area, so it covers nothing.
   One template for every node kind: header - id chips - callout - KPIs - tabs; only the body scrolls. */
.page-card #panel{display:none;flex:0 0 420px;width:420px;min-width:0;flex-direction:column;background:var(--crew-bg);
  border-left:1px solid var(--crew-stroke-1);font:13px/1.45 var(--crew-font);color:var(--crew-text-1);overflow:hidden;}
.page-card #panel.open{display:flex;}
@media (max-width:1100px){
  .page-card #panel.open{position:fixed;top:0;right:0;bottom:0;z-index:50;box-shadow:-6px 0 18px var(--crew-shadow);}
}
.page-card #panel button{font:inherit;color:inherit;background:none;border:0;cursor:pointer;}
.page-card #panel .phead{display:flex;flex-direction:column;gap:10px;padding:14px 16px 12px;flex:0 0 auto;}
.page-card #panel .pnav{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--crew-text-3);}
.page-card #panel .pnav .navback:hover{color:var(--crew-text-1);}
.page-card #panel .pnav .x{margin-left:auto;font-size:14px;line-height:1;color:var(--crew-text-3);}
.page-card #panel .pnav .x:hover{color:var(--crew-text-1);}
.page-card #panel .pid{display:flex;align-items:center;gap:10px;}
.page-card #panel .pidt{min-width:0;}
.page-card #panel .pt{font-size:14px;font-weight:600;line-height:1.2;}
.page-card #panel .ps{font-size:11.5px;color:var(--crew-text-3);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.page-card #panel .pid .pill{margin-left:auto;}
.page-card #panel .avatar{display:inline-grid;place-items:center;flex:0 0 auto;border-radius:999px;width:18px;height:18px;
  font-size:9px;font-weight:600;background:color-mix(in srgb, var(--hue) 22%, transparent);color:var(--hue);}
.page-card #panel .avatar.lg{width:28px;height:28px;font-size:11px;}
.page-card #panel .pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;flex:0 0 auto;border-radius:4px;
  padding:3px 8px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #panel .pill i{width:6px;height:6px;border-radius:50%;background:var(--tone);}
.page-card #panel .ids{display:flex;flex-wrap:wrap;gap:5px;}
.page-card #panel .idc{display:inline-flex;align-items:baseline;gap:5px;max-width:100%;border:1px solid var(--crew-stroke-2);
  border-radius:5px;padding:1px 7px;font-size:10.5px;color:var(--crew-text-3);}
.page-card #panel .idc:hover{border-color:var(--crew-stroke-1);color:var(--crew-text-2);}
.page-card #panel .idc b{font-family:var(--crew-mono);font-weight:400;color:var(--crew-text-2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;max-width:220px;}
.page-card #panel .idc i{font-style:normal;color:var(--crew-text-4);}
.page-card #panel .pcall:empty,.page-card #panel .pkpi:empty{display:none;}
.page-card #panel .callout{display:flex;flex-direction:column;gap:6px;border-radius:6px;padding:10px;
  background:color-mix(in srgb, var(--tone) 7%, transparent);border-left:2px solid var(--tone);}
.page-card #panel .callout .ct{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:500;color:var(--tone);}
.page-card #panel .callout .cb{font-size:12.5px;line-height:1.5;color:var(--crew-text-1);overflow-wrap:anywhere;
  max-height:9.5em;overflow:auto;-webkit-user-select:text;user-select:text;}
.page-card #panel .callout .cm{font-size:10.5px;color:var(--crew-text-3);font-family:var(--crew-mono);overflow-wrap:anywhere;}
.page-card #panel .copy{margin-left:auto;font-size:10.5px;color:var(--crew-text-3);border:1px solid var(--crew-stroke-1);
  border-radius:4px;padding:1px 7px;}
.page-card #panel .kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid var(--crew-stroke-2);border-radius:6px;}
.page-card #panel .kpi{padding:7px 10px;border-left:1px solid var(--crew-stroke-2);min-width:0;}
.page-card #panel .kpi:first-child{border-left:0;}
.page-card #panel .kpi .kv{font-size:13px;font-weight:600;color:var(--crew-text-1);font-variant-numeric:tabular-nums;}
.page-card #panel .kpi .kl{font-size:10px;color:var(--crew-text-4);margin-top:1px;}
.page-card #panel .ptabs{display:flex;align-items:center;padding:0 16px 10px;border-bottom:1px solid var(--crew-stroke-2);flex:0 0 auto;}
.page-card #panel .ptabs[hidden]{display:none;}
.page-card #panel .ptabs .hint{margin-left:auto;font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .seg{display:inline-flex;gap:2px;padding:2px;border-radius:7px;background:var(--crew-fill-1);}
.page-card #panel .seg b{font-weight:500;font-size:11.5px;padding:3px 10px;border-radius:5px;color:var(--crew-text-3);cursor:pointer;}
.page-card #panel .seg b:hover{color:var(--crew-text-1);}
.page-card #panel .seg b.on{background:var(--crew-elevated);color:var(--crew-text-1);box-shadow:0 0 0 1px var(--crew-stroke-2);}
.page-card #panel .seg b span{color:var(--crew-text-4);margin-left:4px;}
.page-card #panel .pbody{flex:1 1 auto;min-height:0;overflow-y:auto;padding:4px 16px 16px;}
.page-card #panel .empty{color:var(--crew-text-3);font-size:12px;padding:14px 0;}
.page-card #panel code{font-family:var(--crew-mono);font-size:.92em;padding:0 4px;border-radius:3px;background:var(--crew-fill-1);}
.page-card #panel .mono{font-family:var(--crew-mono);font-size:11.5px;}
.page-card #panel .bad{color:var(--crew-tone-blocked);}
.page-card #panel .ok{color:var(--crew-tone-running);}
.page-card #panel .warn{color:var(--crew-tone-review);}
.page-card #panel .dim{color:var(--crew-text-4);}
/* Transcript: time gutter (mono) + text (sans); the newest row up to 12 lines, older ones 5, click expands */
.page-card #panel .msg{display:grid;grid-template-columns:62px 1fr;gap:0 8px;padding:10px 0;border-bottom:1px solid var(--crew-stroke-2);cursor:pointer;}
.page-card #panel .msg:last-child{border-bottom:0;}
.page-card #panel .msg time{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);padding-top:3px;align-self:start;
  display:flex;align-items:center;gap:5px;}
.page-card #panel .msg p{margin:0;font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;-webkit-user-select:text;user-select:text;cursor:text;}
.page-card #panel .msg.first p{color:var(--crew-text-1);-webkit-line-clamp:12;}
.page-card #panel .msg.ex p{-webkit-line-clamp:unset;display:block;}
.page-card #panel .msg .md{min-width:0;font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;
  max-height:9em;overflow:hidden;-webkit-user-select:text;user-select:text;cursor:text;}
.page-card #panel .msg.first .md{color:var(--crew-text-1);max-height:22em;}
.page-card #panel .msg.ex .md{max-height:none;}
.page-card #panel .msg.new{animation:sayIn .3s ease-out;}
.page-card #panel .livedot{width:6px;height:6px;border-radius:50%;background:var(--crew-tone-running);display:inline-block;
  animation:beat 1.1s ease-in-out infinite;}
@keyframes beat{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.75)}}
/* Calls: the filter on top, a chip row per tool, folded rows newest first; expanded = args then output */
.page-card #panel .calltools{display:flex;align-items:center;gap:8px;padding:10px 0 8px;}
.page-card #panel .calltools .hint{margin-left:auto;font-size:10.5px;color:var(--crew-text-4);text-align:right;}
.page-card #panel .chips{display:flex;flex-wrap:wrap;gap:5px;padding-bottom:8px;}
.page-card #panel .chip{font-size:10.5px;border:1px solid var(--crew-stroke-1);border-radius:999px;padding:1px 8px;color:var(--crew-text-2);
  font-family:var(--crew-mono);}
.page-card #panel .chip b{font-weight:500;color:var(--crew-text-4);margin-left:3px;}
.page-card #panel .nl{font-size:10.5px;color:var(--crew-text-4);padding-bottom:6px;}
.page-card #panel .call{display:grid;grid-template-columns:14px auto 1fr auto;gap:0 8px;align-items:baseline;
  padding:6px 0;border-bottom:1px solid var(--crew-stroke-2);font-size:11.5px;cursor:pointer;}
.page-card #panel .call .st{font-size:11px;}
.page-card #panel .call .tn{font-family:var(--crew-mono);font-weight:600;color:var(--crew-text-1);}
.page-card #panel .call .ar{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-3);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;min-width:0;}
.page-card #panel .call.failed .ar{color:var(--crew-tone-blocked);}
.page-card #panel .call .of{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .call .ex{grid-column:2 / -1;margin-top:5px;padding:7px 9px;border-radius:5px;background:var(--crew-fill-2);
  font-family:var(--crew-mono);font-size:10.5px;line-height:1.5;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;
  cursor:text;-webkit-user-select:text;user-select:text;}
.page-card #panel .call .ex .ea+.ea{margin-top:4px;}
.page-card #panel .call .ex .eo{margin-top:6px;color:var(--crew-text-3);}
.page-card #panel .call .ex .eo.er{color:var(--crew-tone-blocked);}
/* Details / Contract / Proof / Result: a definition list; the leftover evidence sits in a closed "Raw fields" */
.page-card #panel dl{margin:0;}
.page-card #panel .kvr{display:grid;grid-template-columns:96px 1fr;gap:0 10px;align-items:baseline;padding:7px 0;
  border-bottom:1px solid var(--crew-stroke-2);font-size:12px;}
.page-card #panel .kvr dt{color:var(--crew-text-3);}
.page-card #panel .kvr dd{margin:0;color:var(--crew-text-1);overflow-wrap:anywhere;}
.page-card #panel .kvr dd small{display:block;font-size:10.5px;color:var(--crew-text-3);margin-top:2px;line-height:1.45;}
.page-card #panel .sec{margin-top:14px;}
.page-card #panel .label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);margin-bottom:6px;}
.page-card #panel .prose{font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;}
.page-card #panel .prose.dimp{margin-top:4px;color:var(--crew-text-3);}
.page-card #panel .cm{font-size:10.5px;color:var(--crew-text-3);margin-top:8px;}
.page-card #panel .cmd{font-family:var(--crew-mono);font-size:11px;line-height:1.5;padding:8px 10px;border-radius:5px;
  background:var(--crew-fill-2);color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;}
.page-card #panel details.raw{margin-top:14px;font-size:12px;}
.page-card #panel details.raw summary{cursor:pointer;color:var(--crew-text-3);font-size:11px;}
/* Route: the model chooser's trail, oldest first; a quota wall in the blocked tone */
.page-card #panel .route{display:flex;flex-direction:column;gap:6px;font-size:11.5px;padding-top:10px;}
.page-card #panel .route .rr{display:grid;grid-template-columns:86px 1fr;gap:8px;}
.page-card #panel .route time{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .route span{color:var(--crew-text-2);line-height:1.45;overflow-wrap:anywhere;}
.page-card #panel .route span.bad{color:var(--crew-tone-blocked);}
/* \u2500\u2500 scrollbars, both pages: a hairline track and a small rounded oval thumb in the theme's own tones \u2500\u2500 */
/* \u2500\u2500 the left rail: narrower, its two buttons in the panel's quiet style \u2500\u2500 */
.page-card #rail .rback{margin-top:10px;display:flex;}
.page-card #rail .rbot{margin-top:auto;display:flex;align-items:center;padding-top:10px;border-top:1px solid var(--crew-stroke-2);}
.page-card .railbtn{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;cursor:pointer;text-decoration:none;
  font:inherit;font-size:12px;line-height:1;padding:6px 11px;border-radius:6px;border:1px solid var(--crew-stroke-2);
  background:var(--crew-fill-2);color:var(--crew-text-2);transition:background .15s,border-color .15s,color .15s;}
.page-card .railbtn:hover{background:var(--crew-fill-1);border-color:var(--crew-stroke-1);color:var(--crew-text-1);}
.page-card .railbtn:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:1px;}
.page-card .railbtn .rbtnlabel{font-size:12px;}
.page-card .railbtn.tog{margin-left:auto;padding:6px 9px;font-size:13px;}
.page-card #rail.collapsed .rback,.page-card #rail.collapsed .rbot{justify-content:center;}
.page-card #rail.collapsed .railbtn{padding:6px 8px;}
.page-card #rail.collapsed .railbtn.tog{margin-left:0;}
/* \u2500\u2500 the role filters: one horizontal strip under the top boxes; a role is a small card that focuses its
   nodes, and its last message opens that lane's newest step \u2500\u2500 */
.page-card #rolestrip{flex:0 0 auto;border-bottom:1px solid var(--crew-stroke-2);background:var(--crew-bg);padding:6px 12px;}
.page-card #roster{display:flex;gap:6px;overflow-x:auto;align-items:stretch;}
.page-card .role{flex:0 1 auto;min-width:0;max-width:340px;display:flex;flex-direction:column;justify-content:center;gap:2px;
  padding:5px 11px 5px 9px;border:1px solid var(--crew-stroke-2);border-radius:8px;background:var(--crew-fill-2);cursor:pointer;
  transition:border-color .15s,background .15s;}
.page-card .role:hover{border-color:var(--crew-stroke-1);}
.page-card .role.on{border-color:var(--crew-text-3);background:var(--crew-elevated);}
.page-card .role.all{flex:0 0 auto;}
.page-card .role.all .rn{color:var(--crew-text-1);}
.page-card .role .rl{display:flex;align-items:center;gap:6px;white-space:nowrap;}
.page-card .role .ricon{font-size:11px;width:auto;flex:0 0 auto;}
.page-card .role .rn{font-weight:600;font-size:12px;}
.page-card .role .rc{color:var(--crew-text-4);font-size:10.5px;margin-left:4px;}
.page-card .role .ra{color:var(--crew-text-3);font-size:10.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.page-card .role .rmsg{font-size:11px;line-height:1.35;color:var(--crew-text-3);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;cursor:pointer;}
.page-card .role .rmsg:hover{color:var(--crew-text-1);}
.page-card .role .rmsg.live{color:var(--crew-text-2);}
.page-card .ldot{width:7px;height:7px;border-radius:50%;flex:0 0 auto;opacity:.45;}
.page-card .ldot.act{opacity:1;animation:ldot 1s ease-in-out infinite;}
.page-card #rail .rh{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);margin-bottom:6px;}
.page-card #rail.collapsed .rh{display:none;}
/* the strip stays thin - the canvas is the page: one line per role, the last message inline and cut */
.page-card #rolestrip{padding:4px 12px;}
.page-card #roster{gap:5px;align-items:center;}
.page-card .role{flex-direction:row;align-items:center;gap:8px;padding:2px 10px 2px 8px;border-radius:999px;max-width:420px;}
.page-card .role .ra{display:none;}
.page-card .role .rn{font-size:11.5px;}
.page-card .role .rc{font-size:10px;margin-left:2px;}
.page-card .role .rmsg{min-width:0;max-width:300px;font-size:10.5px;border-left:1px solid var(--crew-stroke-2);padding-left:8px;}
/* the role strip: symbol, name, node count - nothing else; a symbol pulses while its role has a node running */
.page-card .role .ricon{font-size:12px;line-height:1;display:inline-block;}
.page-card .role .ricon.act{animation:ricpulse 1.2s ease-in-out infinite;text-shadow:0 0 6px currentColor;}
@keyframes ricpulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(1.3)}}
@media (prefers-reduced-motion: reduce){ .page-card .role .ricon.act{animation:none} }
/* the brand mark: our logo with no background, the very top left of the header, linking to the overview */
.page-board header a.brand{display:inline-flex;align-items:center;flex:0 0 auto;border-radius:6px}
.page-board header a.brand img{display:block;width:18px;height:18px}
.page-board header a.brand:hover{background:var(--crew-fill-1)}
.page-board header a.brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}
/* the brand mark on the card (steps) view: the same logo with no background, pinned at the top left of the
   event strip and clearing it with #event's left padding; it links to the overview (/), like the board's. */
.page-card{position:relative}
.page-card .brand{position:absolute;top:10px;left:14px;z-index:5;display:inline-flex;align-items:center;border-radius:4px}
.page-card .brand img{display:block;width:12px;height:12px}
.page-card .brand:hover{background:var(--crew-fill-1)}
.page-card .brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}
.page-card #event{padding-left:28px}
/* the graph (graph.css) sits in the page's row where #stage used to: it takes the width the rail and panel leave */
.page-card #row > .crew-graph{flex:1 1 auto;}
/* The panel's tool chips also took the graph's base .chips / .chip rules on the old page (graph.css scopes those to
   .crew-graph now), so the two bits they contributed are restated here: the chip row's margin and the chip's field. */
.page-card #panel .chips{margin:4px 0 0 4px;}
.page-card #panel .chip{background:var(--crew-bg);white-space:nowrap;}

/* \u2500\u2500 narrow layout (the Desktop pane beside the flow pane is ~580 px wide): the status bar is ONE line, the
   least important items step aside by width and stay in the DOM; the title shrinks; the role strip and the rail
   scroll by wheel without drawing a bar. Container queries on the bar and the strip, so the wide page is untouched. \u2500\u2500 */
.page-card #statusbar{container-type:inline-size;container-name:crewbar;flex-wrap:nowrap;white-space:nowrap;}
.page-card #statusbar > *,.page-card #statusbar .meta > *{flex:0 0 auto;}
.page-card #statusbar #cardtitle{flex:0 1 auto;min-width:0;}
.page-card #statusbar .meta{min-width:0;flex:0 1 auto;}
.page-card #statusbar .meta .hints{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;}
.page-card #rail{scrollbar-width:none;}
.page-card #rail::-webkit-scrollbar{display:none;}
.page-card #rolestrip{container-type:inline-size;container-name:crewstrip;}
@container crewbar (max-width:900px){ .page-card #statusbar .hints{display:none;} }
@container crewbar (max-width:620px){ .page-card #statusbar #ractive{display:none;} }
@container crewbar (max-width:480px){ .page-card #statusbar #counts{display:none;} }
@container crewbar (max-width:360px){ .page-card #statusbar #followbtn{display:none;} }
@container crewstrip (max-width:700px){
  .page-card #roster{scrollbar-width:none;}
  .page-card #roster::-webkit-scrollbar{display:none;}
  .page-card .role .rmsg{display:none;}
  .page-card .role{flex:0 0 auto;}
}
`;

  // src/components/EventLine.tsx
  var import_jsx_runtime5 = __toESM(require_jsx_runtime(), 1);
  var T = ({ children }) => /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "t", children });
  function Event({ card }) {
    const nodes = card.nodes || [];
    let lastRun = null, lastEnd = -1;
    for (const n of nodes) {
      if ((n.kind === "run" || n.kind === "verifier") && (n.t1 || 0) > lastEnd) {
        lastEnd = n.t1 || 0;
        lastRun = n;
      }
    }
    let root = null;
    for (const n of nodes) if (n.kind === "card") root = n;
    const rootEv = root && root.evidence || {};
    if (rootEv.block_reason)
      return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(import_jsx_runtime5.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: fmtTime(root.t1 || 0) }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: "coordinator" }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "txt", children: "card " + (card.card_status || "blocked") + ": " + rootEv.block_reason })
      ] });
    let live = null;
    for (const n of nodes) if (n.status === "live" || n.status === "running") live = n;
    if (live) {
      const ls = live.steps || [];
      const s = ls[ls.length - 1];
      return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(import_jsx_runtime5.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: fmtTime(s ? s.ts : live.t1) }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: live.role || "" }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "txt", children: "working now" + (s ? ": " + s.tool + (s.args ? " " + s.args : "") : "") })
      ] });
    }
    let best = null, bestTs = -1;
    if (lastRun) {
      for (const s of lastRun.steps || []) if ((s.ts || 0) >= lastEnd - 2 && (s.ts || 0) > bestTs) {
        bestTs = s.ts || 0;
        best = s;
      }
    }
    const st = card.card_status || "";
    const head = /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(import_jsx_runtime5.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: fmtTime(lastEnd > 0 ? lastEnd : 0) }),
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(T, { children: card.card_role || "coordinator" })
    ] });
    if (best)
      return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(import_jsx_runtime5.Fragment, { children: [
        head,
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "txt", children: (lastRun.role || "") + " " + best.tool + (best.args ? " " + best.args : "") + " - card " + st })
      ] });
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(import_jsx_runtime5.Fragment, { children: [
      head,
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "txt", children: "card " + st + " - " + (card.card_title || "") })
    ] });
  }
  function Kpis({ card }) {
    const s = card.situation || {}, c = s.counts || {};
    const kpi = (v, label, word) => /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "kpi", children: [
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "kv" + (v && word ? " on" : ""), style: { "--tone": toneVar(word || "pending") }, children: +(v || 0) }),
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "kl", children: label })
    ] });
    const title = +(s.runs || 0) + " runs: " + +(c.done || 0) + " done, " + +(c.blocked || 0) + " blocked, " + +(c.failed || 0) + " failed, " + +(c.running || 0) + " running";
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "sitkpis", title, children: [
      kpi(s.runs, "runs"),
      kpi(c.done, "done", "done"),
      kpi(c.blocked, "blocked", "blocked"),
      kpi(c.failed, "failed", "failed"),
      kpi(c.running, "running", "running")
    ] });
  }
  function EventLine({ card }) {
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { id: "event", children: [
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "evmain", children: /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(Event, { card }) }),
      /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(Kpis, { card })
    ] });
  }

  // src/components/Graph.tsx
  var import_react9 = __toESM(require_react(), 1);

  // src/graph-types.ts
  var CW = 250;

  // src/styles/graph.css
  var graph_default = "/* The flow graph and its minimap, ported from scripts/crew_dashboard/crew.css (the .page-card graph rules). Same ids and\n   class names as card.js draws, scoped under .crew-graph instead of body.page-card so the graph can sit in any host\n   (the card page, the Desktop flow pane). Colours come from the --crew-* ladder in base.css only. */\n.crew-graph,.crew-graph *{box-sizing:border-box;margin:0;padding:0}\n.crew-graph{position:relative;display:flex;flex-direction:column;min-height:240px;min-width:0;\n  background:var(--crew-bg);color:var(--crew-text-2);font:12px/1.5 var(--crew-font);outline:none}\n\n.crew-graph .chip-tone{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:4px;\n  padding:2px 8px;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;\n  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}\n.crew-graph .foot .chip-tone{padding:0 6px;font-size:9.5px;}\n.crew-graph .stage{flex:1 1 auto;position:relative;overflow:hidden;background-color:var(--crew-bg);\n  background-image:radial-gradient(circle, var(--crew-stroke-1) 1.3px, transparent 1px);\n  background-size:24px 24px;cursor:grab;}\n.crew-graph .stage{-webkit-user-select:none;user-select:none;}\n.crew-graph .stage.drag{cursor:grabbing;}\n.crew-graph .world{position:absolute;top:0;left:0;transform-origin:0 0;}\n.crew-graph .edges{position:absolute;top:0;left:0;pointer-events:none;overflow:visible;}\n.crew-graph .nodes{position:absolute;top:0;left:0;}\n.crew-graph .node{position:absolute;width:250px;transition:opacity .15s;}\n.crew-graph .node.dim{opacity:.18;}\n.crew-graph .card{position:relative;background:var(--crew-elevated);border:1px solid var(--crew-stroke-1);border-left-width:3px;\n  border-radius:6px;padding:6px 9px 6px 8px;cursor:pointer;}\n.crew-graph .card:hover{border-top-color:var(--crew-text-4);border-right-color:var(--crew-text-4);border-bottom-color:var(--crew-text-4);}\n.crew-graph .node.sel .card{border-top-color:var(--crew-tone-ready);border-right-color:var(--crew-tone-ready);border-bottom-color:var(--crew-tone-ready);}\n.crew-graph .node.alive .card{animation:breathe 1s ease-in-out infinite;}\n@keyframes breathe{0%,100%{box-shadow:0 0 0 0 transparent;}\n  50%{box-shadow:0 0 10px 2px var(--crew-running-glow);}}\n.crew-graph .badge{display:inline-block;border-radius:9px;padding:0 8px;font-size:10px;font-weight:700;\n  color:var(--crew-bg);letter-spacing:.3px;}\n.crew-graph .hdr{display:flex;align-items:center;gap:6px;font-weight:700;font-size:12px;margin-top:2px;}\n.crew-graph .glyph{flex:0 0 auto;width:12px;text-align:center;}\n.crew-graph .node.alive .glyph{animation:glyph 1s steps(1) infinite;}\n@keyframes glyph{50%{opacity:.35;}}\n.crew-graph .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--crew-text-1);}\n.crew-graph .gold{color:var(--crew-text-3);font-size:10px;margin:2px 0 0 0;}\n.crew-graph .desc{color:var(--crew-text-3);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .tools{color:var(--crew-tone-ready);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .foot{display:flex;justify-content:space-between;font-size:10px;}\n.crew-graph .foot .sw{font-weight:700;text-transform:uppercase;}\n.crew-graph .foot .tok{color:var(--crew-text-3);}\n.crew-graph .cellmark{display:none;position:absolute;inset:0;align-items:center;justify-content:center;\n  font-size:34px;font-weight:700;color:var(--crew-bg);}\n.crew-graph .world.cells .card > *:not(.cellmark){visibility:hidden;}\n.crew-graph .world.cells .cellmark{display:flex;}\n.crew-graph .world.cells .chips,.crew-graph .world.cells .steps{visibility:hidden;}\n.crew-graph .chips{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0 0 4px;}\n.crew-graph .chip{font-size:10px;border:1px solid;border-radius:9px;padding:0 7px;background:var(--crew-bg);white-space:nowrap;}\n.crew-graph .chip.done{opacity:.6;}\n.crew-graph .chip.more{color:var(--crew-text-3);border-color:var(--crew-stroke-1);}\n.crew-graph .chip .tk{color:var(--crew-text-3);font-variant-numeric:tabular-nums;}\n.crew-graph .brieftext{margin:3px 0 0 6px;font-size:10px;line-height:1.45;max-height:58px;overflow:hidden;}\n.crew-graph .bline{color:var(--crew-text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .bsrc{color:var(--crew-text-3);font-size:9px;margin:2px 0 0 6px;}\n.crew-graph .node.briefcard .card{border-left-style:dashed;}\n.crew-graph .steps{margin:3px 0 0 6px;font-size:10px;line-height:1.5;max-height:93px;overflow:hidden;}\n.crew-graph .step{color:var(--crew-text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;\n  max-height:16px;will-change:transform,opacity;}\n.crew-graph .step.new{animation:stepIn .32s cubic-bezier(.2,.75,.3,1);}\n.crew-graph .step.out{animation:stepOut .26s ease-in forwards;overflow:hidden;}\n@keyframes stepIn{from{opacity:0;transform:translateY(-7px);max-height:0;}to{opacity:1;transform:translateY(0);max-height:16px;}}\n@keyframes stepOut{from{opacity:.9;transform:translateY(0);max-height:16px;}to{opacity:0;transform:translateY(-5px);max-height:0;}}\n.crew-graph .step:hover{color:var(--crew-text-2);}\n.crew-graph .step .ic{color:var(--crew-text-3);margin-right:4px;}\n.crew-graph .step .tn{font-weight:700;}\n.crew-graph .step .off{color:var(--crew-text-3);margin-left:6px;}\n.crew-graph .step .args{color:var(--crew-text-3);margin-left:6px;opacity:.7;}\n.crew-graph .edge{stroke:var(--crew-stroke-1);stroke-width:1.2;fill:none;}\n.crew-graph .edges .ah{fill:var(--crew-stroke-1);}\n.crew-graph .edges .ah.live{fill:var(--crew-tone-running);}\n.crew-graph .edge.live{stroke:var(--crew-tone-running);stroke-width:1.8;}\n.crew-graph .edge.dim{opacity:.15;}\n.crew-graph .edge.flow{stroke:var(--crew-tone-running);stroke-width:1.4;fill:none;opacity:.45;stroke-dasharray:2 8;\n  animation:flowdash 1.1s linear infinite;pointer-events:none;}\n@keyframes flowdash{to{stroke-dashoffset:-20;}}\n.crew-graph .edge-dot{fill:var(--crew-tone-running);filter:drop-shadow(0 0 3px var(--crew-tone-running));pointer-events:none;}\n.crew-graph .minimap{position:absolute;right:12px;bottom:12px;width:min(200px,34%);height:auto;aspect-ratio:200/130;background:var(--crew-overlay);\n  border:1px solid var(--crew-stroke-1);border-radius:5px;cursor:pointer;}\n.crew-graph .zoomlbl{position:absolute;left:10px;bottom:10px;color:var(--crew-text-3);font-size:10px;}\n/* The follow toggle sat in the card page's status bar; the graph carries its own so the Desktop pane has it too. */\n.crew-graph .gfollow{position:absolute;left:10px;top:10px;z-index:1;font:inherit;font-size:11px;cursor:pointer;\n  background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:10px;padding:1px 8px;color:var(--crew-text-2);}\n.crew-graph .gfollow.on{border-color:var(--crew-tone-running);color:var(--crew-tone-running);}\n.crew-graph .gempty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--crew-text-3);}\n\n/* The Desktop flow pane: a narrow vertical chart of the running card, node boxes joined by straight lines. */\n.crew-flow{display:flex;flex-direction:column;height:100%;min-height:0;overflow:auto;font:12px/1.5 var(--crew-font);color:var(--crew-text-2);}\n.crew-flow .fhead{display:flex;align-items:baseline;gap:8px;min-width:0;padding:10px 12px 4px;}\n.crew-flow .fsel{width:100%;min-width:0;font:inherit;color:var(--crew-text-1);background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:6px;padding:3px 6px;}\n.crew-flow .fid{font-family:var(--crew-mono);color:var(--crew-text-3);font-size:11px;flex:0 0 auto;}\n.crew-flow .ftitle{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--crew-text-1);font-weight:600;}\n.crew-flow .fchart{min-height:0;display:flex;flex-direction:column;align-items:stretch;padding:8px 10px 16px;cursor:pointer;}\n.crew-flow .fchart:focus-visible{outline:1px solid var(--crew-tone-running);}\n.crew-flow .fstepwrap{display:flex;flex-direction:column;align-items:stretch;min-width:0;}\n.crew-flow .fline{align-self:center;display:block;width:20px;height:18px;overflow:visible;}\n.crew-flow .fchart .node{position:relative;width:auto;min-width:0;}\n.crew-flow .fchart .card{cursor:inherit;}\n.crew-flow .fchart:hover .card{border-top-color:var(--crew-text-4);border-right-color:var(--crew-text-4);border-bottom-color:var(--crew-text-4);}\n.crew-flow .fnode.st-failed .card{border-top-color:var(--crew-tone-blocked);border-right-color:var(--crew-tone-blocked);border-bottom-color:var(--crew-tone-blocked);}\n.crew-flow .fnode .tok{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;}\n.crew-flow .fnone{padding:16px 12px;color:var(--crew-text-3);}\n.crew-flow .fboard{color:var(--crew-text-2);}\n\n/* motion means work: no breathing border, glyph blink or travelling dashes for a reader who asked for less */\n@media (prefers-reduced-motion: reduce){\n  .crew-graph .node.alive .card,.crew-graph .node.alive .glyph,.crew-graph .edge.flow{animation:none}\n  .crew-graph .node.alive .card{box-shadow:0 0 0 1px var(--crew-tone-running)}\n  .crew-graph .edge-dot{display:none}\n}\n.crew-flow .fhint{padding:6px 12px 0;font-size:11px;color:var(--crew-text-3);}\n.crew-flow .fcompact{padding:16px 12px;}\n.crew-flow .fhint kbd{font:inherit;background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:3px;padding:0 4px;}\n";

  // src/components/Minimap.tsx
  var import_react8 = __toESM(require_react(), 1);
  var import_jsx_runtime6 = __toESM(require_jsx_runtime(), 1);
  function resolveColour(el2, v) {
    el2.style.color = v;
    return getComputedStyle(el2).color;
  }
  function Minimap({ nodes, pos, world, cam, stage, focusRole, roleColor, onCenter }) {
    const ref = (0, import_react8.useRef)(null);
    const map = (0, import_react8.useRef)(null);
    const [size, setSize] = (0, import_react8.useState)({ w: 200, h: 130 });
    (0, import_react8.useEffect)(() => {
      const c = ref.current;
      if (!c || typeof ResizeObserver === "undefined") return;
      const ro = new ResizeObserver(() => {
        const w = Math.round(c.offsetWidth), h = Math.round(c.offsetHeight);
        if (w > 0 && h > 0) setSize((s) => s.w === w && s.h === h ? s : { w, h });
      });
      ro.observe(c);
      return () => ro.disconnect();
    }, []);
    (0, import_react8.useEffect)(() => {
      const c = ref.current;
      const ctx = c && c.getContext ? c.getContext("2d") : null;
      if (!c || !ctx) return;
      const W = c.width, H = c.height;
      ctx.clearRect(0, 0, W, H);
      const sc = Math.min((W - 12) / world.w, (H - 12) / world.h);
      const ox = (W - world.w * sc) / 2, oy = (H - world.h * sc) / 2;
      map.current = { sc, ox, oy };
      for (const n of nodes) {
        const it = pos[n.id];
        if (!it) continue;
        ctx.globalAlpha = focusRole && n.role !== focusRole ? 0.25 : 1;
        ctx.fillStyle = resolveColour(c, roleColor(n));
        ctx.fillRect(ox + it.x * sc, oy + it.y * sc, Math.max(4, CW * sc), Math.max(3, it.cardH * sc));
      }
      ctx.globalAlpha = 1;
      const vx = -cam.tx / cam.k, vy = -cam.ty / cam.k, vw = stage.w / cam.k, vh = stage.h / cam.k;
      ctx.strokeStyle = resolveColour(c, "var(--crew-text-1)");
      ctx.lineWidth = 1;
      ctx.strokeRect(ox + vx * sc + 0.5, oy + vy * sc + 0.5, vw * sc, vh * sc);
    }, [nodes, pos, world, cam, stage, focusRole, roleColor, size]);
    return /* @__PURE__ */ (0, import_jsx_runtime6.jsx)(
      "canvas",
      {
        className: "minimap",
        ref,
        width: size.w,
        height: size.h,
        onMouseDown: (e) => e.stopPropagation(),
        onClick: (e) => {
          e.stopPropagation();
          const m = map.current;
          const c = ref.current;
          if (!m || !c) return;
          const r = c.getBoundingClientRect();
          onCenter((e.clientX - r.left - m.ox) / m.sc, (e.clientY - r.top - m.oy) / m.sc);
        }
      }
    );
  }

  // src/components/Graph.tsx
  var import_jsx_runtime7 = __toESM(require_jsx_runtime(), 1);
  var GX = 40;
  var GY = 70;
  var PADX = 30;
  var PADY = 18;
  var CELL_ZOOM = 0.5;
  var MAX_CHIPS = 4;
  var MAX_STEP_LINES = 6;
  var COLOUR = {
    running: "var(--crew-tone-running)",
    done: "var(--crew-tone-done)",
    blocked: "var(--crew-tone-blocked)",
    failed: "var(--crew-tone-blocked)",
    pending: "var(--crew-tone-neutral)"
  };
  var CHIP = { pending: "var(--crew-tone-review)", ok: "var(--crew-tone-neutral)", err: "var(--crew-tone-blocked)" };
  var GLYPH = { running: "\u25CF", done: "\u2713", failed: "\u2717", blocked: "\u2717", pending: "\u25CB" };
  var ROLE_ICON2 = { coordinator: "\u25C6", worker: "\u25B2", content: "\u25CF", verifier: "\u2713" };
  var roleIcon2 = (name) => name && ROLE_ICON2[name] || "\u25AA";
  var shortId2 = (s) => s.length <= 14 ? s : s.slice(0, 7) + ".." + s.slice(-5);
  var fmtTokens2 = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : "" + n;
  var pad2 = (x) => (x < 10 ? "0" : "") + x;
  function fmtTime2(sec) {
    if (sec == null) return "";
    const d = new Date(sec * 1e3);
    return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
  }
  function nameFor(n) {
    if (n.kind === "card") return n.title || n.label;
    if (n.kind === "run") return "run " + n.label;
    if (n.kind === "verifier" && String(n.label).indexOf("verdict") === 0) return n.label;
    if (n.kind === "brief") return n.title || "owner brief";
    return n.kind + " " + shortId2(String(n.label));
  }
  function descFor(n) {
    const e = n.evidence || {};
    if (n.kind === "card")
      return "status " + (n.status || "-") + " - coordinator" + (e.writer_role ? " - " + e.writer_role + " did the work" : "") + " - runs " + (e.run_count || 0) + (e.model_override ? "\nworker model: " + e.model_override + (e.provider_override ? " via " + e.provider_override : "") : "");
    if (n.kind === "run") return (e.profile || "-") + " - " + (e.outcome || "-") + " - " + (e.duration || "-");
    if (e.verdict) return e.command || "";
    return (e.model || "-") + " - " + (e.duration || "-");
  }
  function toolsLine(n) {
    const c = n.tool_count || 0;
    return n.last_tool ? "tools " + c + " - " + n.last_tool : "tools " + c;
  }
  function tokensFor(n) {
    const e = n.evidence || {};
    if (e.verdict) return "rc=" + e.rc + " - " + (e.duration_s != null ? e.duration_s + "s" : "");
    const t = e.output_tokens || 0;
    return t ? fmtTokens2(t) + " tok" : "";
  }
  var stepKey = (s) => (s.tool || "?") + "@" + (s.ts || 0) + "|" + String(s.args || "").slice(0, 24);
  function unitIds(nodes, id) {
    const n = nodes.find((x) => x.id === id);
    if (!n) return {};
    const out = { [n.id]: 1 };
    const same = (a, b) => a !== void 0 && a !== null && a === b;
    if (n.kind === "run") {
      const rid = (n.evidence || {}).run_id;
      for (const x of nodes) if (x.kind === "session" && same(x.run_id, rid)) out[x.id] = 1;
    } else if (n.kind === "session") {
      const rid = n.run_id;
      for (const x of nodes) if (x.kind === "run" && same((x.evidence || {}).run_id, rid)) out[x.id] = 1;
    }
    return out;
  }
  function Tk({ ts }) {
    const [now, setNow] = (0, import_react9.useState)(() => Date.now() / 1e3);
    (0, import_react9.useEffect)(() => {
      const t = setInterval(() => setNow(Date.now() / 1e3), 500);
      return () => clearInterval(t);
    }, []);
    const el2 = now - ts;
    if (el2 < 0 || el2 > 300) return null;
    return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "tk", children: " " + el2.toFixed(1) + "s" });
  }
  function Steps({ n, col, onPick }) {
    const seen = (0, import_react9.useRef)(null);
    const all = n.steps || [];
    const keys = /* @__PURE__ */ new Set();
    const lines = all.slice(-MAX_STEP_LINES).filter((s) => !keys.has(stepKey(s)) && !!keys.add(stepKey(s)));
    const marks = (0, import_react9.useRef)(/* @__PURE__ */ new Set());
    const [, redraw] = (0, import_react9.useState)(0);
    const before = seen.current;
    const added = before ? lines.map(stepKey).filter((k) => !before.has(k)) : [];
    added.forEach((k) => marks.current.add(k));
    (0, import_react9.useEffect)(() => {
      seen.current = new Set(keys);
      if (!added.length) return;
      setTimeout(() => {
        added.forEach((k) => marks.current.delete(k));
        redraw((x) => x + 1);
      }, 420);
    });
    return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "steps", children: lines.map((s) => {
      const k = stepKey(s);
      return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
        "div",
        {
          "data-k": k,
          className: "step" + (marks.current.has(k) ? " new" : ""),
          onClick: (ev) => {
            ev.stopPropagation();
            const i = all.findIndex((x) => stepKey(x) === k);
            if (i >= 0) onPick(i);
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "ic", children: "\u25B8" }),
            /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "tn", style: { color: col }, children: s.tool }),
            /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "off", children: s.sec != null ? "t+" + s.sec + "s" : "" }),
            s.args ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "args", children: s.args }) : null
          ]
        },
        k
      );
    }) });
  }
  function NodeView({ n, pageCard, rc, pos, sel, dim, cells, nodeRef, cardRef, onSelect }) {
    const col = COLOUR[n.status] || "var(--crew-tone-neutral)";
    const runs = n.tool_runs || [];
    const total = n.tool_run_total || runs.length;
    const shown = runs.slice(-MAX_CHIPS);
    const live = n.status === "running" || n.status === "pending" || n.t1 == null;
    const d = n.kind === "brief" ? "" : descFor(n);
    return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
      "div",
      {
        ref: nodeRef,
        className: "node" + (n.status === "running" ? " alive" : "") + (sel ? " sel" : "") + (dim ? " dim" : "") + (n.kind === "brief" ? " briefcard" : ""),
        "data-id": n.id,
        style: pos ? { left: pos.x + "px", top: pos.y + "px" } : void 0,
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
            "div",
            {
              ref: cardRef,
              className: "card",
              style: { borderLeftColor: rc, background: cells ? col : void 0 },
              onClick: (ev) => {
                ev.stopPropagation();
                onSelect(n.id);
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "badge", style: { background: rc }, children: roleIcon2(n.role) + " " + (n.role || "?") }),
                /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "gold", children: n.layer + " - " + n.kind + (n.card && n.card !== pageCard ? " - card " + n.card : "") }),
                /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("div", { className: "hdr", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "glyph", style: { color: col }, children: GLYPH[n.status] || "\u25CB" }),
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "name", children: nameFor(n) })
                ] }),
                n.kind === "brief" ? /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(import_jsx_runtime7.Fragment, { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "brieftext", children: (n.brief && n.brief.text || "").split(/\n+/).slice(0, 4).map((ln, i) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "bline", children: ln }, i)) }),
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "bsrc", children: "source: " + (n.brief && n.brief.source || "owner") })
                ] }) : d ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "desc", children: d }) : null,
                n.kind !== "card" && n.kind !== "run" ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "tools", children: toolsLine(n) }) : null,
                /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("div", { className: "foot", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "sw chip-tone", style: { ["--tone"]: col }, children: n.status }),
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "tok", children: tokensFor(n) })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "cellmark", children: (n.role || "?").charAt(0).toUpperCase() })
              ]
            }
          ),
          runs.length ? /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("div", { className: "chips", children: [
            total > shown.length ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("span", { className: "chip more", children: "+" + (total - shown.length) + " more" }) : null,
            shown.map((r, ri) => {
              const cc = CHIP[r.state] || "var(--crew-tone-neutral)";
              const mark = r.state === "ok" ? " \u2713" : r.state === "err" ? " \u2717" : "";
              return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
                "span",
                {
                  className: "chip" + (r.state === "pending" ? "" : " done"),
                  style: { color: cc, borderColor: cc },
                  title: r.state + (r.last_ts ? " - " + fmtTime2(r.last_ts) : ""),
                  children: [
                    r.tool + ((r.count || 0) > 1 ? " x" + r.count : "") + mark,
                    live && ri === shown.length - 1 && r.last_ts ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(Tk, { ts: r.last_ts }) : null
                  ]
                },
                ri + r.tool
              );
            })
          ] }) : null,
          /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(Steps, { n, col, onPick: (i) => onSelect(n.id, i) })
        ]
      }
    );
  }
  var sameLayout = (a, b) => !!a && a.world.w === b.world.w && a.world.h === b.world.h && Object.keys(b.pos).length === Object.keys(a.pos).length && Object.keys(b.pos).every((k) => a.pos[k] && a.pos[k].x === b.pos[k].x && a.pos[k].y === b.pos[k].y && a.pos[k].cardH === b.pos[k].cardH);
  function Graph({ card, height, selectedId, onSelect, focusRole: focusProp, standalone, onFollowChange }) {
    const uid = (0, import_react9.useId)().replace(/[^a-zA-Z0-9]/g, "");
    const arrowId = "arrow" + uid, arrowLiveId = "arrowlive" + uid;
    injectCss("base", base_default);
    injectCss("graph", graph_default);
    const nodes = (0, import_react9.useMemo)(() => card.nodes || [], [card.nodes]);
    const edges = (0, import_react9.useMemo)(() => card.edges || [], [card.edges]);
    const focusRole = focusProp ?? null;
    const [innerSel, setInnerSel] = (0, import_react9.useState)(null);
    const sel = selectedId !== void 0 ? selectedId : innerSel;
    const select = (0, import_react9.useCallback)((id, step) => {
      setInnerSel(id);
      if (onSelect) onSelect(id, step);
    }, [onSelect]);
    const [layout, setLayout] = (0, import_react9.useState)(null);
    const [cam, setCam] = (0, import_react9.useState)({ k: 1, tx: 0, ty: 0 });
    const [follow, setFollow] = (0, import_react9.useState)(false);
    const [drag, setDrag] = (0, import_react9.useState)(false);
    const [stage, setStage] = (0, import_react9.useState)({ w: 0, h: 0 });
    const nodeEls = (0, import_react9.useRef)({});
    const cardEls = (0, import_react9.useRef)({});
    const stageEl = (0, import_react9.useRef)(null);
    const camRef = (0, import_react9.useRef)(cam);
    camRef.current = cam;
    const layoutRef = (0, import_react9.useRef)(layout);
    layoutRef.current = layout;
    const followRef = (0, import_react9.useRef)(follow);
    followRef.current = follow;
    (0, import_react9.useEffect)(() => {
      if (onFollowChange) onFollowChange(follow);
    }, [follow]);
    const fitted = (0, import_react9.useRef)(false);
    const fitLayout = (0, import_react9.useRef)(null);
    const userCam = (0, import_react9.useRef)(false);
    const dragRef = (0, import_react9.useRef)(null);
    const suppressClick = (0, import_react9.useRef)(false);
    const prevStageW = (0, import_react9.useRef)(null);
    const world = layout ? layout.world : { w: 400, h: 300 };
    const roleColor = (0, import_react9.useCallback)((n) => {
      const r = (card.roles || []).find((x) => x.name === n.role);
      return n.role_color || r && r.color || "var(--crew-tone-neutral)";
    }, [card.roles]);
    const stageSize = () => {
      const s = stageEl.current;
      return { w: s ? s.clientWidth : 0, h: s ? s.clientHeight : 0 };
    };
    const fitView = (0, import_react9.useCallback)(() => {
      const w = layoutRef.current ? layoutRef.current.world : { w: 400, h: 300 };
      const s = stageSize();
      const k = Math.max(0.12, Math.min(Math.min(s.w / w.w, s.h / w.h) * 0.92, 1.2));
      setCam({ k, tx: (s.w - w.w * k) / 2, ty: Math.max(10, (s.h - w.h * k) / 2) });
    }, []);
    const centerOn = (0, import_react9.useCallback)((id) => {
      const it = layoutRef.current && layoutRef.current.pos[id];
      if (!it) return;
      const s = stageSize(), k = camRef.current.k;
      setCam({ k, tx: s.w / 2 - (it.x + CW / 2) * k, ty: s.h / 2 - (it.y + it.cardH / 2) * k });
    }, []);
    const followTarget = () => {
      let best = null, bt = -1;
      let pool = nodes.filter((n) => n.status === "running");
      if (!pool.length) pool = nodes;
      for (const n of pool) {
        const t = n.last_ts || 0;
        if (t >= bt) {
          bt = t;
          best = n;
        }
      }
      return best;
    };
    const stopFollow = () => {
      if (followRef.current) setFollow(false);
    };
    const cardId = card.card_id;
    (0, import_react9.useLayoutEffect)(() => {
      fitted.current = false;
      userCam.current = false;
      setInnerSel(null);
    }, [cardId]);
    (0, import_react9.useLayoutEffect)(() => {
      const layers = {};
      let maxLayer = 0;
      for (const n of nodes) {
        (layers[n.layer] = layers[n.layer] || []).push(n);
        if (n.layer > maxLayer) maxLayer = n.layer;
      }
      const pos = {};
      let y = PADY, totalW = PADX;
      for (let l = 0; l <= maxLayer; l++) {
        const lyr = (layers[l] || []).slice().sort((a, b) => (a.x || 0) - (b.x || 0));
        if (!lyr.length) continue;
        let x = PADX, maxH = 0;
        for (const n of lyr) {
          const el2 = nodeEls.current[n.id], ce = cardEls.current[n.id];
          pos[n.id] = { x, y, cardH: ce && ce.offsetHeight || 40 };
          maxH = Math.max(maxH, el2 && el2.offsetHeight || 0);
          x += CW + GX;
        }
        totalW = Math.max(totalW, x - GX + PADX);
        y += maxH + GY;
      }
      const next = { pos, world: { w: Math.max(totalW, 300), h: Math.max(y - GY + PADY, 200) } };
      setLayout((prev) => sameLayout(prev, next) ? prev : next);
    }, [nodes]);
    (0, import_react9.useEffect)(() => {
      if (!layout) return;
      if (!fitted.current) {
        fitted.current = true;
        fitLayout.current = layout;
        fitView();
      } else if (layout !== fitLayout.current && !userCam.current) {
        fitLayout.current = layout;
        fitView();
      }
      if (followRef.current) {
        const t = followTarget();
        if (t) centerOn(t.id);
      }
    }, [layout, follow, nodes]);
    (0, import_react9.useEffect)(() => {
      const el2 = stageEl.current;
      if (!el2 || typeof ResizeObserver === "undefined") return;
      const ro = new ResizeObserver(() => {
        const s = stageSize();
        setStage((p) => p.w === s.w && p.h === s.h ? p : s);
        const prev = prevStageW.current;
        prevStageW.current = s.w;
        if (!layoutRef.current) return;
        if (userCam.current && prev !== null) {
          const d = (s.w - prev) / 2;
          if (d) setCam((c) => ({ ...c, tx: c.tx + d }));
        } else if (!userCam.current) fitView();
      });
      ro.observe(el2);
      return () => ro.disconnect();
    }, [fitView]);
    (0, import_react9.useEffect)(() => {
      const st = stageEl.current;
      if (!st) return;
      const wheel = (e) => {
        e.preventDefault();
        const r = st.getBoundingClientRect(), c = camRef.current;
        const mx = e.clientX - r.left, my = e.clientY - r.top;
        const k2 = Math.max(0.12, Math.min(2.5, c.k * Math.exp(-e.deltaY * 15e-4)));
        const wx = (mx - c.tx) / c.k, wy = (my - c.ty) / c.k;
        userCam.current = true;
        stopFollow();
        setCam({ k: k2, tx: mx - wx * k2, ty: my - wy * k2 });
      };
      st.addEventListener("wheel", wheel, { passive: false });
      const move = (e) => {
        const d = dragRef.current;
        if (!d) return;
        const dx = e.clientX - d.x, dy = e.clientY - d.y;
        if (!d.moved && Math.abs(dx) + Math.abs(dy) > 4) {
          d.moved = true;
          setDrag(true);
          stopFollow();
        }
        if (d.moved) {
          userCam.current = true;
          setCam({ k: camRef.current.k, tx: d.tx + dx, ty: d.ty + dy });
        }
      };
      const up = () => {
        const d = dragRef.current;
        if (d && d.moved) {
          suppressClick.current = true;
          setTimeout(() => {
            suppressClick.current = false;
          }, 0);
        }
        dragRef.current = null;
        setDrag(false);
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
      return () => {
        st.removeEventListener("wheel", wheel);
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
      };
    }, []);
    const onSelectNode = (id, step) => {
      if (!suppressClick.current) select(id, step);
    };
    const units = unitIds(nodes, sel);
    const cells = cam.k < CELL_ZOOM;
    const g = 24 * cam.k;
    const byId = {};
    if (layout) {
      for (const n of nodes) if (layout.pos[n.id]) byId[n.id] = { n, p: layout.pos[n.id] };
    }
    const key = (e) => {
      if (e.key === "f") {
        stopFollow();
        userCam.current = false;
        fitView();
      } else if (e.key === "F") setFollow((f) => !f);
      else if (e.key === "0") {
        stopFollow();
        userCam.current = true;
        setCam({ k: 1, tx: 0, ty: 0 });
      } else if (e.key === "Escape") select(null);
    };
    return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "crew-scope crew-graph", style: height ? { height: height + "px" } : void 0, tabIndex: 0, onKeyDown: key, children: /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
      "div",
      {
        ref: stageEl,
        className: "stage" + (drag ? " drag" : ""),
        style: { backgroundSize: g + "px " + g + "px", backgroundPosition: cam.tx + "px " + cam.ty + "px" },
        onClick: () => {
          if (!suppressClick.current && sel) select(null);
        },
        onMouseDown: (e) => {
          if (e.button !== 0) return;
          e.preventDefault();
          dragRef.current = { x: e.clientX, y: e.clientY, tx: camRef.current.tx, ty: camRef.current.ty, moved: false };
          suppressClick.current = false;
        },
        onDoubleClick: () => {
          stopFollow();
          userCam.current = false;
          fitView();
        },
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(
            "div",
            {
              className: "world" + (cells ? " cells" : ""),
              style: { transform: "translate(" + cam.tx + "px," + cam.ty + "px) scale(" + cam.k + ")" },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)("svg", { className: "edges", width: world.w, height: world.h, style: { width: world.w + "px", height: world.h + "px" }, children: [
                  /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("defs", { children: [[arrowId, "ah"], [arrowLiveId, "ah live"]].map(([id, cls]) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("marker", { id, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse", children: /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("path", { d: "M0,0 L10,5 L0,10 z", className: cls }) }, id)) }),
                  edges.map((e, i) => {
                    const a = byId[e.from], b = byId[e.to];
                    if (!a || !b) return null;
                    const x1 = a.p.x + CW / 2, y1 = a.p.y + a.p.cardH, x2 = b.p.x + CW / 2, y2 = b.p.y;
                    const c = Math.max(y2 - y1, 0) * 0.55;
                    const d = "M" + x1 + " " + y1 + " C " + x1 + " " + (y1 + c) + ", " + x2 + " " + (y2 - c) + ", " + x2 + " " + y2;
                    const live = b.n.status === "running";
                    const off = !!focusRole && a.n.role !== focusRole && b.n.role !== focusRole;
                    return /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(import_react9.Fragment, { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("path", { d, className: "edge" + (live ? " live" : "") + (off ? " dim" : ""), markerEnd: "url(#" + (live ? arrowLiveId : arrowId) + ")" }),
                      live && !off ? /* @__PURE__ */ (0, import_jsx_runtime7.jsxs)(import_jsx_runtime7.Fragment, { children: [
                        /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("path", { d, className: "edge flow" }),
                        /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("circle", { r: "2.6", className: "edge-dot", children: /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("animateMotion", { dur: "1.6s", repeatCount: "indefinite", path: d, fill: "freeze" }) })
                      ] }) : null
                    ] }, e.from + ">" + e.to + i);
                  })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "nodes", style: { width: world.w + "px", height: world.h + "px" }, children: nodes.map((n) => /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
                  NodeView,
                  {
                    n,
                    pageCard: card.card_id,
                    rc: roleColor(n),
                    pos: layout ? layout.pos[n.id] : void 0,
                    sel: !!units[n.id],
                    dim: !!focusRole && n.role !== focusRole,
                    cells,
                    nodeRef: (el2) => {
                      nodeEls.current[n.id] = el2;
                    },
                    cardRef: (el2) => {
                      cardEls.current[n.id] = el2;
                    },
                    onSelect: onSelectNode
                  },
                  n.id
                )) })
              ]
            }
          ),
          standalone ? /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("button", { type: "button", className: "gfollow" + (follow ? " on" : ""), onClick: (e) => {
            e.stopPropagation();
            setFollow((f) => !f);
          }, children: "follow " + (follow ? "on" : "off") }) : null,
          /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(
            Minimap,
            {
              nodes,
              pos: layout ? layout.pos : {},
              world,
              cam,
              stage,
              focusRole,
              roleColor,
              onCenter: (wx, wy) => {
                const s = stageSize();
                userCam.current = true;
                stopFollow();
                setCam({ k: camRef.current.k, tx: s.w / 2 - wx * camRef.current.k, ty: s.h / 2 - wy * camRef.current.k });
              }
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime7.jsx)("div", { className: "zoomlbl", children: Math.round(cam.k * 100) + "%" + (cells ? " - cells" : "") })
        ]
      }
    ) });
  }

  // src/components/Panel.tsx
  var import_react10 = __toESM(require_react(), 1);

  // src/card-model.ts
  var TAB_SETS = {
    step: ["Transcript", "Calls", "Details"],
    card: ["Contract", "Route", "Details"],
    verifier: ["Proof", "Runs", "Details"],
    close: ["Result", "Details"],
    brief: []
  };
  var LATEST_N = 6;
  var roleDef = (card, name) => (card.roles || []).find((r) => r.name === name) || null;
  var nodeById = (card, id) => (card.nodes || []).find((n) => n.id === id) || null;
  function unitOf(card, n) {
    if (!n) return null;
    let run = null, sess = null;
    if (n.kind === "run") {
      run = n;
      const rid = (n.evidence || {}).run_id;
      for (const x of card.nodes || []) if (x.kind === "session" && x.run_id !== void 0 && x.run_id !== null && x.run_id === rid) sess = x;
    } else if (n.kind === "session") {
      sess = n;
      if (n.run_id !== void 0 && n.run_id !== null) run = nodeById(card, "run:" + n.run_id);
    }
    return { run, session: sess, main: n, key: run ? run.id : n.id };
  }
  function panelKind(n) {
    if (n.kind === "run" || n.kind === "session" || n.kind === "subagent") return "step";
    if (n.kind === "card" || n.kind === "verifier" || n.kind === "close" || n.kind === "brief") return n.kind;
    return "step";
  }
  function getSelectedNode(card, selected) {
    if (selected) {
      const n = nodeById(card, selected);
      if (n) return n;
    }
    let best = null, bestTs = -1;
    for (const n of card.nodes || []) for (const s of n.steps || []) {
      const t = s.ts || 0;
      if (t > bestTs) {
        bestTs = t;
        best = n;
      }
    }
    return best || card.nodes && card.nodes[0] || null;
  }
  function modelPick(card, startedAt) {
    let pick = null;
    for (const r of card.route || []) if (r.kind !== "quota_wall" && (!startedAt || (r.ts || 0) <= startedAt + 5)) pick = r;
    return pick;
  }
  function panelModel(card, n) {
    const ev = n.evidence || {}, kind = panelKind(n), u = unitOf(card, n);
    const m = { kind, tabs: TAB_SETS[kind], kpis: [] };
    const other = n.card && n.card !== card.card_id ? n.card : null;
    if (kind === "step" && u) {
      const run = u.run, sess = u.session || (n.kind === "subagent" ? n : null);
      const re = (run || {}).evidence || {}, se = (sess || {}).evidence || {};
      const lv = (sess || run || n).live || {};
      const live = lv.state === "pending" || (run || n).status === "running";
      m.role = n.role;
      m.unit = u;
      m.title = cap1(n.role) + " \xB7 " + (run ? "run " + (re.run_id !== void 0 ? re.run_id : run.label) : n.kind === "subagent" ? "subagent" : "session");
      m.sub = live ? "running " + fmtAgo((run || n).t0 || 0).replace(/ ago$/, "") + (lv.tool ? " \xB7 " + lv.tool : "") : (re.profile || se.profile_name || "") + (re.ended_at || (sess || {}).t1 ? " \xB7 ended " + hhmm2(re.ended_at || sess.t1) : "");
      if (other) m.sub += " \xB7 card " + other;
      const outcome = re.outcome || (sess || n).status;
      m.pill = [live ? "Running" : cap1(String(outcome || "").replace(/_/g, " ")), live ? "running" : outcome];
      m.chips = [
        ["model", "model", se.model || ev.model, "panelModCopy"],
        ["session_id", "session", se.session_id || ev.session_id, "panelSidCopy"],
        ["kanban id", "card", other || card.card_id, "panelCidCopy"]
      ];
      if (run && !live && outcome && outcome !== "completed" && (re.summary || re.error))
        m.callout = ["Why this run stopped", re.summary || re.error, re.summary && re.error ? re.error : "", outcome, "panelWhyCopy"];
      const tin = +se.input_tokens || 0, tout = +se.output_tokens || 0;
      const calls = +(se.tool_call_count || (sess || n).tool_count || 0) || 0;
      const failed = +(se.calls_failed !== void 0 && se.calls_failed !== null ? se.calls_failed : (sess || n).steps ? (sess || n).steps.filter((s) => s.state === "err").length : 0) || 0;
      m.kpis = [
        { value: re.duration || se.duration || "-", label: "duration" },
        sess ? { value: fmtTokens(tin + tout), label: "tokens \xB7 " + fmtTokens(tout) + " out" } : null,
        sess ? { value: String(calls), label: "tool calls", failed } : null
      ];
      m.src = sess || run || n;
      m.run = run;
      m.sess = sess;
      m.live = live;
      m.failed = failed;
      m.calls = calls;
    } else if (kind === "card") {
      m.role = "coordinator";
      m.title = "Coordinator \xB7 card";
      m.sub = (card.card_title || "") + (ev.run_count ? " \xB7 " + ev.run_count + " run" + (ev.run_count === 1 ? "" : "s") : "");
      m.pill = [cap1(card.card_status || n.status), card.card_status || n.status];
      m.chips = [
        ["model", "model", ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "", "panelModCopy"],
        ["session_id", "session", ev.coordinator || "", "panelSidCopy"],
        ["kanban id", "card", card.card_id, "panelCidCopy"]
      ];
    } else if (kind === "verifier") {
      m.role = "verifier";
      m.title = "Verifier \xB7 verdict";
      const runsV = ev.review_runs || [], lastRun = runsV[runsV.length - 1] || {};
      m.sub = ev.by ? "by " + ev.by + (ev.ts ? " \xB7 " + hhmm2(ev.ts) : "") : runsV.length ? runsV.length + " review run(s)" : "no verdict yet";
      m.pill = [ev.verdict || "unverified", ev.verdict || "unverified"];
      m.chips = [
        ["model", "model", "", "panelModCopy"],
        ["session_id", "session", lastRun.session_id || "", "panelSidCopy"],
        ["kanban id", "card", card.card_id, "panelCidCopy"]
      ];
      if (ev.verdict === "FAIL")
        m.callout = ["Verification failed", ev.output_head || "(no output recorded)", ev.command ? "command: " + ev.command : "", "FAIL", "panelWhyCopy"];
      m.kpis = [
        { value: ev.rc === null || ev.rc === void 0 ? "-" : String(ev.rc), label: "rc" },
        { value: ev.duration_s === null || ev.duration_s === void 0 ? "-" : ev.duration_s + "s", label: "duration" },
        { value: String(ev.verdict_count || 0), label: "verdict lines" }
      ];
    } else if (kind === "close") {
      m.role = "coordinator";
      m.title = "Coordinator \xB7 close";
      m.sub = ev.completed_at ? "completed " + dayTime(ev.completed_at) : "not closed";
      m.pill = [cap1(ev.status || n.status), ev.status || n.status];
      m.chips = [["model", "model", "", "panelModCopy"], ["session_id", "session", "", "panelSidCopy"], ["kanban id", "card", card.card_id, "panelCidCopy"]];
    } else if (kind === "brief") {
      m.role = n.role || "owner";
      m.title = "Owner brief";
      m.sub = ev.source ? "from " + ev.source : "";
      m.chips = [["kanban id", "card", card.card_id, "panelCidCopy"]];
    }
    return m;
  }

  // src/components/Runs.tsx
  var import_jsx_runtime8 = __toESM(require_jsx_runtime(), 1);
  function Md({ text }) {
    const parts = String(text === null || text === void 0 ? "" : text).split(/`([^`\n]+)`/);
    return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(import_jsx_runtime8.Fragment, { children: parts.map((p, i) => i % 2 ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("code", { children: p }, i) : p) });
  }
  function transcriptRows(m, expanded, renderMarkdown) {
    const src = m.src || {};
    const lines = (src.text || []).slice().reverse();
    return lines.map((l, i) => {
      const key = String(l.ts || "") + "|" + String(l.text || "").slice(0, 80);
      return {
        key,
        cls: "msg" + (i === 0 ? " first" : "") + (expanded[key] ? " ex" : ""),
        children: /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)(import_jsx_runtime8.Fragment, { children: [
          /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("time", { children: [
            i === 0 && m.live ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("i", { className: "livedot" }) : null,
            l.ts ? fmtTime(l.ts) : ""
          ] }),
          renderMarkdown ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { className: "md", children: renderMarkdown(String(l.raw || l.text || "")) }) : /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("p", { children: /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(Md, { text: l.text }) })
        ] })
      };
    });
  }
  function callGroups(m, views) {
    const steps = (m.src || {}).steps || [];
    const view = views[m.unit.key] || ((m.failed || 0) > 0 ? "failed" : "latest");
    const picked = view === "failed" ? steps.filter((s) => s.state === "err") : steps.slice(-LATEST_N);
    return { view, groups: groupParallel(picked).reverse(), steps };
  }
  function callRows(m, cg, open) {
    return cg.groups.map((g) => {
      const key = g.k + "|" + (g.args[0] || "").slice(0, 24);
      const isOpen = !!open[m.unit.key + "|" + key];
      const icon = g.state === "err" ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "st bad", children: "\u2715" }) : g.state === "pending" ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "st warn", children: "\u25CF" }) : /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "st ok", children: "\u2713" });
      const prev = g.state === "err" && (g.note || g.out) ? g.note || g.out : g.args[0] || "";
      return {
        key,
        cls: "call" + (isOpen ? " open" : "") + (g.state === "err" ? " failed" : ""),
        children: /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)(import_jsx_runtime8.Fragment, { children: [
          icon,
          /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "tn", children: g.tool + (g.args.length > 1 ? " \xD7" + g.args.length : "") }),
          /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "ar", children: prev }),
          /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "of", children: offLabel(g) }),
          isOpen ? /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("div", { className: "ex", children: [
            g.args.filter((a) => a).map((a, i) => /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { className: "ea", children: a }, i)),
            /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { className: "eo" + (g.state === "err" ? " er" : ""), children: stepStatus(g) })
          ] }) : null
        ] })
      };
    });
  }
  function CallsHead({ m, cg, onView }) {
    const total = m.calls || cg.steps.length, loaded = cg.steps.length;
    const nf = m.failed || 0, latest = Math.min(LATEST_N, loaded);
    const chips = /* @__PURE__ */ new Map();
    for (const t of (m.src || {}).tool_runs || []) chips.set(t.tool, (chips.get(t.tool) || 0) + t.count);
    const failedLoaded = cg.steps.filter((s) => s.state === "err").length;
    const hint = cg.view === "failed" ? nf + " failed of " + total + " calls" + (nf > failedLoaded ? " (older failures not loaded)" : "") : "latest " + latest + " of " + total + " calls";
    const notLoaded = Math.max(0, total - loaded);
    return /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)(import_jsx_runtime8.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("div", { className: "calltools", children: [
        /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("div", { className: "seg cbfilter", role: "tablist", children: [
          /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("b", { className: cg.view === "failed" ? "on" : "", "data-view": "failed", onClick: () => onView("failed"), children: [
            "Failed",
            /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { children: nf })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("b", { className: cg.view === "latest" ? "on" : "", "data-view": "latest", onClick: () => onView("latest"), children: [
            "Latest",
            /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { children: latest })
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("span", { className: "hint", children: hint })
      ] }),
      chips.size ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { className: "chips", children: [...chips].map(([t, c]) => /* @__PURE__ */ (0, import_jsx_runtime8.jsxs)("span", { className: "chip", children: [
        t,
        /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("b", { children: c })
      ] }, t)) }) : null,
      notLoaded ? /* @__PURE__ */ (0, import_jsx_runtime8.jsx)("div", { className: "nl", children: notLoaded + " earlier ok call" + (notLoaded === 1 ? "" : "s") + " not loaded" }) : null
    ] });
  }

  // src/components/Panel.tsx
  var import_jsx_runtime9 = __toESM(require_jsx_runtime(), 1);
  var tone2 = (word) => ({ "--tone": toneVar(word) });
  function Pill({ text, word }) {
    if (!text) return null;
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("span", { className: "pill", style: tone2(word || text), children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("i", {}),
      text
    ] });
  }
  function Avatar2({ card, role }) {
    const hue = roleDef(card, role)?.color || "var(--crew-tone-neutral)";
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "avatar lg", style: { "--hue": hue }, children: cap1(role || "?").slice(0, 1) });
  }
  function kvRow(key, val, sub) {
    if (val === null || val === void 0 || val === "" || val === false) return null;
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "kvr", children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("dt", { children: key }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("dd", { children: [
        val,
        sub ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("small", { children: sub }) : null
      ] })
    ] }, key);
  }
  function rawFields(evs, skip) {
    const rows = [];
    for (const ev of evs) for (const k of Object.keys(ev || {})) {
      const v = ev[k];
      if (skip[k] || v === null || v === void 0 || v === "" || typeof v === "object") continue;
      rows.push(kvRow(k, /at$/.test(k) || k === "ts" ? typeof v === "number" ? fmtTime(v) : String(v) : String(v)));
      skip[k] = 1;
    }
    return rows.length ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("details", { className: "raw", children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("summary", { children: "Raw fields" }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("dl", { children: rows })
    ] }) : null;
  }
  function RoleAbout({ card, role }) {
    const rd = roleDef(card, role) || { purpose: "", proof: "" };
    if (!rd.purpose && !rd.proof) return null;
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "sec", children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "label", children: "About the " + role + " role" }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "prose", children: rd.purpose || "" }),
      rd.proof ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "prose dimp", children: "Proof: " + rd.proof }) : null
    ] });
  }
  function Route({ card }) {
    const rows = card.route || [];
    if (!rows.length) return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: "No model was routed for this card: its runs used the role profile's own model." });
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "route", children: rows.map((r, i) => {
      const wall = r.kind === "quota_wall";
      const what = wall ? "quota wall" + (r.wall_number ? " #" + r.wall_number : "") + " on " + (r.model || "?") + " - " + (r.why || "") : (r.kind === "reroute" ? "re-routed to " : "picked ") + (r.provider ? r.provider + "/" : "") + (r.model || "?") + (r.why ? " - " + r.why : "");
      return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "rr", children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("time", { children: dayTime(r.ts) }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: wall ? "bad" : "", children: what })
      ] }, i);
    }) });
  }
  function detailsStep(card, m) {
    const re = (m.run || {}).evidence || {}, se = (m.sess || {}).evidence || {};
    const src = m.src || {};
    const pick = modelPick(card, re.started_at || src.t0);
    const skip = {
      model: 1,
      session_id: 1,
      run_id: 1,
      profile: 1,
      profile_name: 1,
      started_at: 1,
      ended_at: 1,
      duration: 1,
      input_tokens: 1,
      output_tokens: 1,
      message_count: 1,
      tool_call_count: 1,
      calls_failed: 1,
      summary: 1,
      error: 1,
      outcome: 1
    };
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("dl", { children: [
        kvRow("Model pick", pick ? pick.why || pick.model : "", pick ? "routed " + dayTime(pick.ts) + " \xB7 " + (pick.provider || "") + "/" + (pick.model || "") : ""),
        kvRow("Profile", re.profile || se.profile_name || ""),
        kvRow("Started", fmtTime(re.started_at || src.t0), (re.ended_at ? "ended " + fmtTime(re.ended_at) : "") + (re.duration ? " \xB7 " + re.duration : "")),
        kvRow("Tokens", m.sess ? fmtTokens(se.input_tokens) + " in \xB7 " + fmtTokens(se.output_tokens) + " out" : "", se.message_count ? se.message_count + " messages" : ""),
        kvRow("Prompt", src.prompt ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "mono", children: src.prompt }) : "")
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(RoleAbout, { card, role: m.role }),
      rawFields([re, se], skip)
    ] });
  }
  function tabBody(card, n, m, tab) {
    const ev = n.evidence || {};
    if (m.kind === "card") {
      if (tab === "Contract")
        return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("dl", { children: [
          kvRow("Done when", ev.done_when ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: ev.done_when }) : ""),
          kvRow("Writer", (ev.writer_role || "") + (ev.assignee ? " \xB7 " + ev.assignee : "")),
          kvRow("Verifier", ev.verifier || ""),
          kvRow("Model pin", ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "none - the role profile's model"),
          kvRow("Budget", ev.ceiling ? fmtTokens(ev.spent) + " of " + fmtTokens(ev.ceiling) + " tokens" : ""),
          kvRow("Result", ev.result ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: ev.result }) : "")
        ] }) };
      if (tab === "Route") return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Route, { card }) };
      const dec = ev.decisions || [];
      return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
        dec.length ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "sec", children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "label", children: "Coordinator decisions" }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "route", children: dec.map((d, i) => /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "rr", children: [
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("time", { children: dayTime(d.ts) }),
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: d.label || d.decision || "" })
          ] }, i)) })
        ] }) : null,
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(RoleAbout, { card, role: "coordinator" }),
        rawFields([ev], { done_when: 1, writer_role: 1, assignee: 1, verifier: 1, model_override: 1, provider_override: 1, ceiling: 1, spent: 1, result: 1, block_reason: 1, status: 1, decisions: 1 })
      ] }) };
    }
    if (m.kind === "verifier") {
      if (tab === "Proof")
        return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("dl", { children: [
            kvRow("Done when", ev.done_when ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: ev.done_when }) : ""),
            kvRow("Command", ev.command ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "mono", children: ev.command }) : ""),
            kvRow("Verdict", ev.verdict || "unverified", ev.by ? "by " + ev.by + (ev.ts ? " \xB7 " + dayTime(ev.ts) : "") : "")
          ] }),
          ev.output_head ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "sec", children: [
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "label", children: "Output" }),
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "cmd", children: ev.output_head })
          ] }) : null
        ] }) };
      if (tab === "Runs") {
        const rs = ev.review_runs || [];
        return { doc: rs.length ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "route", children: rs.map((r, i) => /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "rr", children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("time", { children: "run " + r.run_id }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: (r.profile || "") + " \xB7 " + (r.outcome || "-") + " \xB7 " + (r.duration || "-") + (r.summary ? " - " + r.summary : "") })
        ] }, i)) }) : /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: "No review run: the proof was run without a verifier session." }) };
      }
      return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(RoleAbout, { card, role: "verifier" }),
        rawFields([ev], { done_when: 1, command: 1, verdict: 1, by: 1, ts: 1, output_head: 1, rc: 1, duration_s: 1, verdict_count: 1, review_runs: 1 })
      ] }) };
    }
    if (m.kind === "close") {
      if (tab === "Result")
        return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("dl", { children: [
            kvRow("Status", ev.status || ""),
            kvRow("Completed", dayTime(ev.completed_at))
          ] }),
          ev.result ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "prose", children: /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: ev.result }) }) : /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: "No result recorded yet." })
        ] }) };
      return { doc: rawFields([ev], { status: 1, completed_at: 1, result: 1 }) };
    }
    if (m.kind === "brief")
      return { doc: /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "prose", children: /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: ev.text || ev.brief || n.brief || "" }) }),
        ev.source || ev.by ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "cm", children: [ev.source, ev.by, ev.origin].filter((x) => x).join(" \xB7 ") }) : null
      ] }) };
    if (tab === "Details") return { doc: detailsStep(card, m) };
    return null;
  }
  function readTab(kind) {
    try {
      return window.localStorage.getItem("crewTab." + kind);
    } catch {
      return null;
    }
  }
  function storeTab(kind, tab) {
    try {
      window.localStorage.setItem("crewTab." + kind, tab);
    } catch {
    }
  }
  function Panel({ hash, askedTab, onTabApplied }) {
    const ui = useCardUi();
    const { card } = ui;
    const { renderMarkdown } = useCrewHost();
    const [tabs, setTabs] = (0, import_react10.useState)({});
    const [views, setViews] = (0, import_react10.useState)({});
    const [openCalls, setOpenCalls] = (0, import_react10.useState)({});
    const [expanded, setExpanded] = (0, import_react10.useState)({});
    const [flash, setFlash] = (0, import_react10.useState)({});
    const seen = (0, import_react10.useRef)({});
    const bodyRef = (0, import_react10.useRef)(null);
    const open = ui.panelOpen;
    const n = open ? getSelectedNode(card, ui.selected) : null;
    const m = n ? panelModel(card, n) : null;
    const ukey = n ? m.unit && m.unit.key || n.id : "";
    let tab = null;
    if (m && m.tabs.length) {
      const asked = askedTab && n && askedTab.node === n.id ? m.tabs.find((t) => t.toLowerCase() === String(askedTab.tab).toLowerCase()) : void 0;
      const want = asked || tabs[m.kind] || readTab(m.kind);
      tab = m.tabs.indexOf(want || "") >= 0 ? want : m.tabs[0];
    }
    (0, import_react10.useEffect)(() => {
      if (m && askedTab && n && askedTab.node === n.id) {
        const t = m.tabs.find((x) => x.toLowerCase() === String(askedTab.tab).toLowerCase());
        if (t) {
          storeTab(m.kind, t);
          setTabs((s) => ({ ...s, [m.kind]: t }));
        }
        onTabApplied();
      }
    });
    (0, import_react10.useLayoutEffect)(() => {
      if (bodyRef.current) bodyRef.current.scrollTop = 0;
    }, [ukey, tab, open]);
    (0, import_react10.useEffect)(() => {
      if (!hash || typeof window === "undefined") return;
      const parts = [];
      for (const kv of (window.location.hash || "").replace(/^#/, "").split("&")) if (kv && !/^(node|tab)=/.test(kv)) parts.push(kv);
      if (open && n) {
        parts.push("node=" + encodeURIComponent(n.id));
        if (tab) parts.push("tab=" + tab.toLowerCase());
      }
      const h = parts.length ? "#" + parts.join("&") : "";
      if (h !== window.location.hash) {
        try {
          window.history.replaceState(null, "", window.location.pathname + window.location.search + h);
        } catch {
        }
      }
    }, [hash, open, n && n.id, ukey, tab]);
    const rowsT = open && m && tab === "Transcript" ? transcriptRows(m, expanded, renderMarkdown) : null;
    const seenNow = rowsT ? seen.current[ukey] : void 0;
    (0, import_react10.useEffect)(() => {
      if (!rowsT) return;
      const s = seen.current[ukey] = seen.current[ukey] || /* @__PURE__ */ new Set();
      for (const r of rowsT) s.add(r.key);
    });
    if (!open || !n || !m) return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { id: "panel", className: open ? "open" : "" });
    const copy = (id, text) => {
      copyText(text, (ok) => {
        setFlash((f) => ({ ...f, [id]: { until: Date.now() + 1600, label: ok ? "copied" : "select + copy" } }));
        setTimeout(() => setFlash((f) => ({ ...f })), 1700);
      });
    };
    const flashLabel = (id, dflt) => flash[id] && flash[id].until > Date.now() ? flash[id].label : dflt;
    const chip = (c) => {
      const [key, label, value, copyId] = c;
      return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(
        "button",
        {
          type: "button",
          className: "idc",
          id: copyId,
          "data-k": key,
          "data-v": value || "",
          title: "copy " + key,
          "aria-label": "copy " + key,
          onClick: (e) => {
            e.stopPropagation();
            copy(copyId, key + ": " + (value || ""));
          },
          children: [
            label,
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("b", { className: "idv", children: value || "none" }),
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("i", { children: flash[copyId] && flash[copyId].until > Date.now() ? flash[copyId].label : "\u29C9" })
          ]
        },
        copyId
      );
    };
    let rows = [];
    let top = null;
    let doc = null;
    let listCls = "plist";
    const body = tabBody(card, n, m, tab);
    if (body) doc = body.doc;
    else if (tab === "Transcript") {
      rows = rowsT || [];
      listCls = "plist transcript";
      if (!rows.length) doc = /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: "No text yet, this run has only made tool calls." });
    } else {
      const cg = callGroups(m, views);
      top = /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(CallsHead, { m, cg, onView: (v) => setViews((s) => ({ ...s, [ukey]: v })) });
      listCls = "plist calls";
      rows = callRows(m, cg, openCalls);
      if (!cg.steps.length) doc = /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: "No tool call recorded for this run." });
      else if (!cg.groups.length) doc = /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "empty", children: cg.view === "failed" ? "No failed call." : "No call." });
    }
    const noSel = () => !String(window.getSelection ? window.getSelection() || "" : "");
    const dedup = /* @__PURE__ */ new Map();
    const kpis = m.kpis.filter((k) => k);
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { id: "panel", className: "open", children: [
      /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "phead", children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "pnav", children: [
          n.kind === "card" ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: "Card" }) : /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("button", { type: "button", className: "navback", "data-node": "card:" + card.card_id, onClick: () => ui.select("card:" + card.card_id), children: "\u2039 Card" }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "dim", children: "/" }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: m.role || n.kind }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("button", { type: "button", className: "x", title: "close (esc)", onClick: () => ui.closePanel(), children: "\u2715" })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "pid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Avatar2, { card, role: m.role }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "pidt", children: [
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "pt", children: m.title }),
            m.sub ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "ps", children: m.sub }) : null
          ] }),
          m.pill ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Pill, { text: m.pill[0], word: m.pill[1] }) : null
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "ids", children: (m.chips || []).map(chip) }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "pcall", children: m.callout ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "callout", style: tone2(m.callout[3] || "blocked"), children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "ct", children: [
            m.callout[0],
            /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(
              "button",
              {
                type: "button",
                className: "copy",
                id: m.callout[4],
                "data-copytext": m.callout[1],
                onClick: (e) => {
                  e.stopPropagation();
                  copy(m.callout[4], m.callout[1]);
                },
                children: flashLabel(m.callout[4], "copy")
              }
            )
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "cb", children: /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Md, { text: m.callout[1] }) }),
          m.callout[2] ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "cm", children: m.callout[2] }) : null
        ] }) : null }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "pkpi", children: kpis.length ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "kpis", children: kpis.map((k, i) => /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "kpi", children: [
          /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "kv", children: k.value }),
          /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "kl", children: [
            k.label,
            k.failed ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
              " ",
              "\xB7",
              " ",
              /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "bad", children: k.failed + " failed" })
            ] }) : null
          ] })
        ] }, i)) }) : null })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "ptabs", hidden: !m.tabs.length, children: m.tabs.length ? /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(import_jsx_runtime9.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "seg", role: "tablist", children: m.tabs.map((t) => /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)(
          "b",
          {
            className: t === tab ? "on" : "",
            "data-tab": t,
            onClick: () => {
              storeTab(m.kind, t);
              setTabs((s) => ({ ...s, [m.kind]: t }));
            },
            children: [
              t,
              t === "Calls" ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: m.calls || 0 }) : t === "Route" ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { children: (card.route || []).length }) : null
            ]
          },
          t
        )) }),
        tab === "Transcript" ? /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("span", { className: "hint", children: "newest first" }) : null
      ] }) : null }),
      /* @__PURE__ */ (0, import_jsx_runtime9.jsxs)("div", { className: "pbody", ref: bodyRef, children: [
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "ptop", children: top }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: listCls, children: rows.map((r) => {
          const c = dedup.get(r.key) || 0;
          dedup.set(r.key, c + 1);
          const isNew = tab === "Transcript" && seenNow && !seenNow.has(r.key);
          return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(
            "div",
            {
              "data-key": r.key,
              className: r.cls + (isNew ? " new" : ""),
              onClick: (e) => {
                if (!noSel()) return;
                if (tab === "Calls") {
                  if (e.target.closest(".ex")) return;
                  const k = ukey + "|" + r.key;
                  setOpenCalls((s) => ({ ...s, [k]: !s[k] }));
                } else setExpanded((s) => ({ ...s, [r.key]: !s[r.key] }));
              },
              children: r.children
            },
            r.key + (c ? "#" + c : "")
          );
        }) }),
        /* @__PURE__ */ (0, import_jsx_runtime9.jsx)("div", { className: "pdoc", children: doc })
      ] })
    ] });
  }

  // src/components/Brief.tsx
  var import_jsx_runtime10 = __toESM(require_jsx_runtime(), 1);
  function Brief({ card }) {
    const b = briefFields(card.nodes || []);
    return /* @__PURE__ */ (0, import_jsx_runtime10.jsxs)("div", { id: "briefsec", hidden: !b, children: [
      /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("div", { className: "rh", children: "brief" }),
      /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("div", { id: "briefText", children: b ? b.text : "" }),
      /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("div", { id: "briefSrc", children: b ? b.src : "" })
    ] });
  }

  // src/components/Tokens.tsx
  var import_jsx_runtime11 = __toESM(require_jsx_runtime(), 1);
  function Tokens({ card }) {
    const t = card.tokens || {};
    const ceil = +(t.ceiling || 0), used = +(t.used || 0);
    const pct = ceil ? Math.round(1e3 * used / ceil) / 10 : 0;
    const row = (id, label, value, color) => /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { className: "tokrow", id, children: [
      /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("span", { className: "tk", children: label }),
      /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("span", { className: "tv", style: color ? { color } : void 0, children: value })
    ] });
    return /* @__PURE__ */ (0, import_jsx_runtime11.jsxs)("div", { id: "toksec", children: [
      /* @__PURE__ */ (0, import_jsx_runtime11.jsx)("div", { className: "rh", children: "tokens" }),
      row("tokCeiling", "ceiling", fmtExact(ceil)),
      row("tokUsed", "used (billed)", fmtExact(used)),
      row("tokRaw", "raw total", fmtExact(t.raw_total)),
      row("tokCalls", "api calls", fmtExact(t.calls)),
      row("tokPct", "of ceiling", pct.toFixed(1) + "%", ceil ? budgetTone(pct) : void 0)
    ] });
  }

  // src/components/Rail.tsx
  var import_jsx_runtime12 = __toESM(require_jsx_runtime(), 1);
  function Rail({ card, collapsed, onToggle, onBack, href = "/" }) {
    const arrow = collapsed ? "\u203A" : "\u2039";
    return /* @__PURE__ */ (0, import_jsx_runtime12.jsxs)("div", { id: "rail", className: collapsed ? "collapsed" : "", children: [
      /* @__PURE__ */ (0, import_jsx_runtime12.jsx)(Tokens, { card }),
      /* @__PURE__ */ (0, import_jsx_runtime12.jsx)(Brief, { card }),
      /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("div", { className: "rback", children: /* @__PURE__ */ (0, import_jsx_runtime12.jsxs)("a", { className: "railbtn", href, title: "back to the board", onClick: (e) => {
        if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();
        onBack();
      }, children: [
        "\u2039",
        /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("span", { className: "rbtnlabel", children: " board" })
      ] }) }),
      /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("div", { className: "rbot", children: /* @__PURE__ */ (0, import_jsx_runtime12.jsx)("button", { className: "railbtn tog", id: "railBot", type: "button", title: collapsed ? "expand the sidebar" : "collapse the sidebar", onClick: onToggle, children: arrow }) })
    ] });
  }

  // src/components/Roster.tsx
  var import_jsx_runtime13 = __toESM(require_jsx_runtime(), 1);
  function Roster() {
    const { card, focusRole, setFocusRole } = useCardUi();
    const colour = (c) => ({ color: c });
    return /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("div", { id: "rolestrip", children: /* @__PURE__ */ (0, import_jsx_runtime13.jsxs)("div", { id: "roster", children: [
      /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("div", { className: "role all" + (focusRole ? "" : " on"), onClick: () => setFocusRole(null), children: /* @__PURE__ */ (0, import_jsx_runtime13.jsxs)("div", { className: "rl", children: [
        /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "ricon", children: "\u25A6" }),
        /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "rn", children: focusRole ? "\u2190 show all roles" : "all roles" }),
        /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "rc", children: (card.node_count || 0) + " nodes" })
      ] }) }),
      (card.roles || []).map((r) => /* @__PURE__ */ (0, import_jsx_runtime13.jsx)(
        "div",
        {
          className: "role" + (focusRole === r.name ? " on" : ""),
          title: (r.purpose || "") + (r.active ? " - working now" : ""),
          onClick: () => setFocusRole(focusRole === r.name ? null : r.name),
          children: /* @__PURE__ */ (0, import_jsx_runtime13.jsxs)("div", { className: "rl", children: [
            /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "ricon" + (r.active ? " act" : ""), style: colour(r.color), children: roleIcon(r.name) }),
            /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "rn", style: colour(r.color), children: r.name }),
            /* @__PURE__ */ (0, import_jsx_runtime13.jsx)("span", { className: "rc", children: r.nodes + (r.nodes === 1 ? " node" : " nodes") })
          ] })
        },
        r.name
      ))
    ] }) });
  }

  // src/components/Scrubber.tsx
  var import_jsx_runtime14 = __toESM(require_jsx_runtime(), 1);
  function Scrubber() {
    const { card, selected, selStep, selectStep } = useCardUi();
    const sel = getSelectedNode(card, selected);
    const steps = sel ? sel.steps || [] : [];
    return /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("div", { id: "scrubwrap", children: /* @__PURE__ */ (0, import_jsx_runtime14.jsxs)("div", { id: "scrubber", children: [
      /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("div", { className: "track" }),
      !steps.length ? /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("span", { className: "tl left", children: "no steps" }) : /* @__PURE__ */ (0, import_jsx_runtime14.jsxs)(import_jsx_runtime14.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("span", { className: "tl left", children: tickTime(steps[0]) }),
        /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("span", { className: "tl right", children: tickTime(steps[steps.length - 1]) }),
        steps.map((_s, i) => /* @__PURE__ */ (0, import_jsx_runtime14.jsx)(
          "div",
          {
            className: "tick" + (i === selStep ? " active" : "") + (i === steps.length - 1 ? " playhead" : ""),
            style: { left: (steps.length === 1 ? 50 : i / (steps.length - 1) * 100) + "%" },
            onClick: () => selectStep(sel.id, i),
            children: /* @__PURE__ */ (0, import_jsx_runtime14.jsx)("div", { className: "diam" })
          },
          i
        ))
      ] })
    ] }) });
  }

  // src/components/StatusBar.tsx
  var import_jsx_runtime15 = __toESM(require_jsx_runtime(), 1);
  function StatusBar({ card, paused, follow, onFollow, onBack, href = "/" }) {
    const act = (card.roles || []).filter((r) => r.active).map((r) => r.name);
    return /* @__PURE__ */ (0, import_jsx_runtime15.jsxs)("div", { id: "statusbar", children: [
      /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "pill", children: "crew" }),
      /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "live" + (paused ? " paused" : ""), id: "live", children: paused ? "PAUSED" : "LIVE" }),
      /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "cardtitle", id: "cardtitle", children: card.card_title || card.card_id || "" }),
      /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "pill", id: "ractive", children: "roles active: " + (act.length ? act.join(", ") : "none") }),
      /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "pill btn" + (follow ? " on" : ""), id: "followbtn", onClick: onFollow, children: "follow " + (follow ? "on" : "off") }),
      /* @__PURE__ */ (0, import_jsx_runtime15.jsxs)("span", { className: "meta", children: [
        /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { id: "counts", children: (card.node_count || 0) + " nodes - " + (card.edge_count || 0) + " edges" }),
        /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("a", { href, onClick: (e) => {
          if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
          e.preventDefault();
          onBack();
        }, children: "overview" }),
        /* @__PURE__ */ (0, import_jsx_runtime15.jsx)("span", { className: "hints", children: "space pause - r refresh - f or double-click fit - 0 zoom - F follow - ? help - o overview" })
      ] })
    ] });
  }

  // src/components/TopArea.tsx
  var import_react11 = __toESM(require_react(), 1);
  var import_jsx_runtime16 = __toESM(require_jsx_runtime(), 1);
  var tone3 = (word) => ({ "--tone": toneVar(word) });
  function CopyButton({ id, title, text, className = "copy", label = "copy", stop = true }) {
    const [shown, setShown] = (0, import_react11.useState)(label);
    return /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(
      "button",
      {
        type: "button",
        className,
        id,
        title,
        "aria-label": title,
        onClick: (e) => {
          if (stop) e.stopPropagation();
          copyText(text(), (ok) => {
            setShown(ok ? "copied" : "select + copy");
            setTimeout(() => setShown(label), 1600);
          });
        },
        children: shown
      }
    );
  }
  function Field({ label, value, copy }) {
    if (value === null || value === void 0 || value === "") return null;
    return /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("span", { className: "fp", children: [
      /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "fk", children: label }),
      /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "fv", title: value, children: value }),
      copy ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(CopyButton, { id: copy.id, title: copy.title, text: () => value }) : null
    ] });
  }
  function TopArea({ card, openChat, onAction }) {
    const { actions } = useCrewHost();
    const s = card.situation || {};
    const cls = s.headline && s.headline.indexOf("stopped") === 0 ? "blocked" : s.headline === "finished" ? "done" : s.headline && s.headline.indexOf("working") === 0 ? "running" : "";
    const st = card.card_status || "-";
    const fp = s.first_pass || {};
    const un = s.units || {};
    const kids = (s.children || []).length;
    const target = coordinatorTarget(card.coordinator);
    const report = card.card_status === "done" ? card.report || "" : "";
    const reason = report || s.reason || s.why || "";
    const you = (s.reason_actor || (s.reason ? "nobody" : "")) === "you" || cls === "blocked";
    const age = s.reason_age_s;
    const spinText = s.repeat_text || "";
    const quiet = !s.repeat || !spinText;
    return /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "toparea", className: quiet ? "two" : "", children: [
      /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { className: "tcell", id: "topSit", children: [
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { className: "tch", children: "card" }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "sit", className: "sit", children: [
          /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("span", { className: "pill sh", style: tone3(st), children: [
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("i", {}),
            st
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "pill sb " + cls, style: tone3(cls || "pending"), children: s.headline || "-" }),
          fp.rounds ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "pill sb " + (fp.first_pass ? "done" : "blocked"), style: tone3(fp.first_pass ? "PASS" : "FAIL"), children: fp.first_pass ? "passed first try" : +(fp.passes || 0) ? +(fp.fails || 0) + " fail(s) before pass" : "check failed" }) : null,
          un.total ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "pill sd", style: tone3((un.passed || 0) >= un.total ? "PASS" : "pending"), children: "units " + +(un.passed || 0) + " of " + +un.total + " passed" }) : null,
          kids ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "pill sd", style: tone3("pending"), children: "children " + kids }) : null
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "sitfields", className: "fields", children: [
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(Field, { label: "model", value: card.card_model || "" }),
          card.card_created_at ? /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(Field, { label: "started", value: fmtAge(Date.now() / 1e3 - card.card_created_at) }) : null,
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(Field, { label: "kanban id", value: card.card_id || "", copy: { id: "cardIdCopy", title: "copy the kanban id" } }),
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(Field, { label: "coordinator", value: card.coordinator || "", copy: { id: "cardCoCopy", title: "copy the coordinator session" } }),
          target && openChat && !actions ? /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)(import_jsx_runtime16.Fragment, { children: [
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "brk" }),
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "fp openrow", children: /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(
              "button",
              {
                type: "button",
                className: "copy",
                id: "cardCoOpen",
                title: "open the chat this card came from",
                "aria-label": "open the chat this card came from",
                onClick: (e) => {
                  e.stopPropagation();
                  openChat(target.profile, target.session);
                },
                children: "open chat \u2197"
              }
            ) })
          ] }) : null
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(ActionBar, { card, openChat, onDone: onAction || (() => {
        }) })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { className: "tcell", id: "topWhy", children: [
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { className: "tch", id: "whyHead", children: report ? "done report" : "pending reason" }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { className: "tce", id: "sitboxNone", hidden: !!reason, children: "nothing pending" }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "sitbox", hidden: !reason, className: !reason ? void 0 : report ? "done" : you ? "you" : "nobody", children: [
          /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "sitboxHead", children: [
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "sbl", children: report ? "delivered" : you ? "needs you" : "waiting - nobody has to act" }),
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: report ? "sb done" : "sb " + cls, children: report ? "done" : (card.card_status || "-") + (s.headline ? " - " + s.headline : "") }),
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(CopyButton, { id: "sitCopy", title: "copy the pending reason", text: () => (card.card_id ? card.card_id + "\n\n" : "") + reason })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { id: "sitboxWhy", children: reason }),
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { id: "sitboxMeta", children: report ? "what the owner is sent when the card ends" : "source: " + (s.reason_source || "task") + " - recorded " + fmtAge(age) + (age !== null && age !== void 0 ? " (" + age + "s)" : "") })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { className: "tcell", id: "topSpin", hidden: quiet, children: [
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { className: "tch", children: "repeated stops" }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { className: "tce", id: "spinboxNone", hidden: !quiet, children: "not spinning" }),
        /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "spinbox", hidden: quiet, children: [
          /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)("div", { id: "spinboxHead", children: [
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { id: "spinboxCount", children: (s.repeat_stops || 0) + " of " + (s.runs || 0) + " runs stopped on the same reason" }),
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("span", { className: "sbl", children: "spinning" }),
            /* @__PURE__ */ (0, import_jsx_runtime16.jsx)(CopyButton, { id: "spinCopy", title: "copy the repeated reason", text: () => spinText })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("div", { id: "spinboxText", children: spinText })
        ] })
      ] })
    ] });
  }

  // src/components/CardPage.tsx
  var import_jsx_runtime17 = __toESM(require_jsx_runtime(), 1);
  function readRail() {
    try {
      return window.localStorage.getItem("crewRailCollapsed") === "1";
    } catch {
      return false;
    }
  }
  function CardPage({ api, id, onBack, openChat, hash = false, boardHref = "/" }) {
    injectCss("base", base_default);
    injectCss("card", card_default);
    const [paused, setPaused] = (0, import_react12.useState)(false);
    const { card, error, loading, reload } = useCard(api, id, 2e3, paused);
    const [selected, setSelected] = (0, import_react12.useState)(null);
    const [selStep, setSelStep] = (0, import_react12.useState)(-1);
    const [panelOpen, setPanelOpen] = (0, import_react12.useState)(false);
    const [focusRole, setFocusRole] = (0, import_react12.useState)(null);
    const [railCollapsed, setRailCollapsed] = (0, import_react12.useState)(() => readRail() || hash && /rail=collapsed/.test(window.location.hash));
    const [help, setHelp] = (0, import_react12.useState)(false);
    const [askedTab, setAskedTab] = (0, import_react12.useState)(null);
    const root = (0, import_react12.useRef)(null);
    const suppressClick = (0, import_react12.useRef)(false);
    (0, import_react12.useEffect)(() => {
      setSelected(null);
      setSelStep(-1);
      setPanelOpen(false);
      setFocusRole(null);
    }, [id]);
    (0, import_react12.useEffect)(() => {
      if (!hash) return;
      const apply = () => {
        let node = null, tab = null;
        for (const kv of (window.location.hash || "").replace(/^#/, "").split("&")) {
          const i = kv.indexOf("=");
          if (i < 0) continue;
          const k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
          if (k === "role") setFocusRole(v || null);
          if (k === "node" && v) node = v;
          if (k === "tab" && v) tab = v;
        }
        if (node) {
          setSelected((prev) => prev === node ? prev : node);
          setPanelOpen(true);
        }
        if (node && tab) setAskedTab({ node, tab });
      };
      apply();
      window.addEventListener("hashchange", apply);
      return () => window.removeEventListener("hashchange", apply);
    }, [hash]);
    const select = (0, import_react12.useCallback)((nodeId) => {
      setSelected(nodeId);
      setSelStep(-1);
      setPanelOpen(true);
    }, []);
    const selectStep = (0, import_react12.useCallback)((nodeId, i) => {
      setSelected(nodeId);
      setSelStep(i);
      setPanelOpen(true);
    }, []);
    const closePanel = (0, import_react12.useCallback)(() => {
      setSelected(null);
      setPanelOpen(false);
    }, []);
    const toggleRail = (0, import_react12.useCallback)(() => {
      setRailCollapsed((c) => {
        try {
          window.localStorage.setItem("crewRailCollapsed", c ? "0" : "1");
        } catch {
        }
        return !c;
      });
    }, []);
    const keyRef = (0, import_react12.useRef)({ paused, selected, reload, onBack, closePanel });
    keyRef.current = { paused, selected, reload, onBack, closePanel };
    (0, import_react12.useEffect)(() => {
      const onKey = (e) => {
        if (e.ctrlKey || e.metaKey || e.altKey || !isCrewKey(e, root.current)) return;
        const k = keyRef.current;
        if (e.code === "Space") {
          e.preventDefault();
          setPaused((p) => !p);
        } else if (e.key === "r" || e.key === "R") k.reload();
        else if (e.key === "?") setHelp((h) => !h);
        else if (e.key === "o" || e.key === "O") k.onBack();
        else if (e.key === "f" || e.key === "F" || e.key === "0") toGraph(root.current, e.key);
        else if (e.key === "Escape") {
          setHelp(false);
          if (k.selected) k.closePanel();
          else setFocusRole(null);
        }
      };
      document.addEventListener("keydown", onKey);
      return () => document.removeEventListener("keydown", onKey);
    }, []);
    const [follow, setFollow] = (0, import_react12.useState)(false);
    const ui = (0, import_react12.useMemo)(
      () => card && {
        card,
        api,
        selected,
        selStep,
        focusRole,
        follow,
        paused,
        panelOpen,
        select,
        selectStep,
        closePanel,
        setFocusRole,
        setFollow: () => toGraph(root.current, "F"),
        suppressClick
      },
      [card, api, selected, selStep, focusRole, follow, paused, panelOpen, select, selectStep, closePanel]
    );
    if (!card || !ui)
      return /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("div", { className: "page-card crew-scope", ref: root, "data-card": id, children: /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("div", { style: { padding: 16 }, children: error ? "Crew could not load: " + error : loading ? "Loading..." : "" }) });
    return /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(CardUiContext.Provider, { value: ui, children: /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { className: "page-card crew-scope", ref: root, "data-card": card.card_id, children: [
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("a", { className: "brand", href: boardHref, title: "overview", "aria-label": "crew overview", onClick: (e) => {
        if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();
        onBack();
      }, children: /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("img", { src: MARK_URI, alt: "", width: 26, height: 26 }) }),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(EventLine, { card }),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { id: "main", children: [
        /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(TopArea, { card, openChat, onAction: reload }),
        /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Roster, {}),
        /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { id: "row", children: [
          /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Rail, { card, collapsed: railCollapsed, onToggle: toggleRail, onBack, href: boardHref }),
          /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(
            Graph,
            {
              card,
              api,
              selectedId: panelOpen ? selected : null,
              focusRole,
              onFollowChange: setFollow,
              onSelect: (nodeId, step) => {
                if (nodeId === null) closePanel();
                else if (step !== void 0) selectStep(nodeId, step);
                else select(nodeId);
              }
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Panel, { hash, askedTab, onTabApplied: () => setAskedTab(null) })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Scrubber, {}),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(StatusBar, { card, paused, follow, onFollow: () => toGraph(root.current, "F"), onBack, href: boardHref }),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(Help, { open: help })
    ] }) });
  }
  function toGraph(root, key) {
    const g = root && root.querySelector(".crew-graph");
    if (g) g.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  }
  function Help({ open }) {
    const row = (k, text) => /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { className: "row", children: [
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("kbd", { children: k }),
      text
    ] });
    return /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { id: "help", className: open ? "open" : "", children: [
      /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("div", { className: "h", children: "keys" }),
      row("space", "pause / resume polling"),
      row("r", "refresh once"),
      row("f", "fit view"),
      row("0", "reset zoom"),
      row("F", "follow the newest active node"),
      /* @__PURE__ */ (0, import_jsx_runtime17.jsxs)("div", { className: "row", children: [
        /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("kbd", { children: "wheel" }),
        "zoom - ",
        /* @__PURE__ */ (0, import_jsx_runtime17.jsx)("kbd", { children: "drag" }),
        "pan - zoomed out, cards become status blocks"
      ] }),
      row("?", "toggle this help"),
      row("o", "open overview"),
      row("esc", "close help, clear role focus")
    ] });
  }

  // src/route.ts
  function parseLocation(pathname, search) {
    const m = /^\/card\/([A-Za-z0-9_-]+)\/?$/.exec(pathname);
    if (m) return { page: "card", id: m[1] };
    if (/^\/crew\/?$/.test(pathname)) {
      const id = new URLSearchParams((search || "").replace(/^\?/, "")).get("card") || "";
      if (/^[A-Za-z0-9_-]+$/.test(id)) return { page: "card", id };
    }
    return { page: "board", all: /[?&]all=1/.test(search), .../[?&]older=1/.test(search) ? { older: true } : {} };
  }
  function hrefFor(r) {
    if (r.page === "card") return "/card/" + r.id;
    const q = [r.all ? "all=1" : "", r.older ? "older=1" : ""].filter(Boolean).join("&");
    return q ? "/?" + q : "/";
  }

  // src/open-card.ts
  var CARD_ID = /^[A-Za-z0-9_-]+$/;
  function cardFromSearch(search) {
    const id = new URLSearchParams((search || "").replace(/^\?/, "")).get("card") || "";
    return CARD_ID.test(id) ? id : "";
  }

  // src/browser.tsx
  var import_jsx_runtime18 = __toESM(require_jsx_runtime(), 1);
  function snapshotApi(snap) {
    return {
      get: async (path) => {
        if (path === "/card/" + encodeURIComponent(snap.card_id) + ".json") return snap;
        throw new Error(path + ": this file shows one card as it was when it was written");
      },
      post: async () => ({ ok: false, status: 405, text: "this file is a snapshot\n" })
    };
  }
  function App({ opts }) {
    const snap = window.__CREW_SNAPSHOT;
    const hosted = !!opts.base;
    const api = (0, import_react13.useMemo)(() => snap ? snapshotApi(snap) : fetchApi(opts.base || "", opts.fetch, !hosted), [snap, opts.base, opts.fetch, hosted]);
    const start = () => {
      if (snap) return { page: "card", id: snap.card_id };
      if (!hosted) return parseLocation(window.location.pathname, window.location.search);
      const shared = cardFromSearch(window.location.search);
      return shared ? { page: "card", id: shared } : { page: "board", all: false };
    };
    const [route, setRoute] = (0, import_react13.useState)(start);
    (0, import_react13.useEffect)(() => {
      if (snap || hosted) return;
      const pop = () => setRoute(parseLocation(window.location.pathname, window.location.search));
      window.addEventListener("popstate", pop);
      return () => window.removeEventListener("popstate", pop);
    }, [snap, hosted]);
    const go = (r) => {
      if (snap) return;
      if (!hosted) try {
        window.history.pushState(null, "", hrefFor(r));
      } catch {
      }
      setRoute(r);
    };
    const home = () => go({ page: "board", all: false });
    const openChat = opts.openChat ?? (typeof window.__crewOpenChat === "function" ? (profile, session) => window.__crewOpenChat(profile, session) : void 0);
    return route.page === "card" ? /* @__PURE__ */ (0, import_jsx_runtime18.jsx)(CardPage, { api, id: route.id, onBack: home, openChat, hash: !hosted && !snap }) : /* @__PURE__ */ (0, import_jsx_runtime18.jsx)(
      Board,
      {
        api,
        onOpenCard: (id) => go({ page: "card", id }),
        home,
        flags: hosted ? { all: false } : { all: route.all, ...route.older ? { older: true } : {} }
      }
    );
  }
  function mount(el2, opts = {}) {
    const root = (0, import_client.createRoot)(el2);
    root.render(/* @__PURE__ */ (0, import_jsx_runtime18.jsx)(App, { opts }));
    return () => root.unmount();
  }
  window.__crewMount = mount;
  var el = document.getElementById("crew-app");
  if (el && !el.hasAttribute("data-manual")) {
    el.setAttribute("data-crew-shell", "");
    mount(el, { base: el.getAttribute("data-base") || "" });
  }
})();
