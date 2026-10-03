// Web Storage throws in private mode / when the quota is exhausted, and a
// throw from a best-effort read or write must never take the caller down.
// Reading the global itself can throw too (Firefox with storage disabled
// raises SecurityError on `window.sessionStorage` access), so the callers hand
// over a thunk and the access happens inside the try, not at the call site.
// Reads return null on failure (indistinguishable from "not set", which is the
// right fallback everywhere we use it); writes and removes report success.

export function storageGet(getStorage, key) {
  try {
    return getStorage().getItem(key)
  } catch {
    return null
  }
}

export function storageSet(getStorage, key, value) {
  try {
    getStorage().setItem(key, value)

    return true
  } catch {
    return false
  }
}

export function storageRemove(getStorage, key) {
  try {
    getStorage().removeItem(key)

    return true
  } catch {
    return false
  }
}

// The two storages this app uses, as thunks ready to pass in.
export const session = () => sessionStorage

export const local = () => localStorage
