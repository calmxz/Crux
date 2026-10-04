// EventTarget for X-Cost-Warning soft-cap notifications carried back on
// successful API responses. Parallel to errorBus — plain JS module so
// apiClient can dispatch without a Vue setup context. Listeners (toasts,
// banners) attach from within Vue components.
export const costBus = new EventTarget()

export function reportCostWarning(detail) {
  costBus.dispatchEvent(new CustomEvent('cost-warning', { detail }))
}

// Shared by request() and the raw multipart upload fetch (#398), which both
// see successful responses that may carry the soft-cap header.
export function reportCostWarningFrom(resp, path) {
  const warn = resp.headers?.get?.('x-cost-warning')

  if (warn) reportCostWarning({ header: warn, path })
}
