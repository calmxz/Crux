// Builds the cost-cap-reached toast message/summary from a mapCapError() info
// object. Scope-aware: 'global' (service-wide budget) never has per-user
// spend figures (mapCapError nulls them out), so it must not render
// "$null / $null" -- match the wording used by
// frontend/src/components/chat/CapBanners.vue ("Service daily budget
// reached." / "Daily cost limit reached.").
export function dailyCapToastMessage(info, whenText) {
  return {
    message: `Daily limit reached (${info.used}/${info.cap}). Resets at ${whenText}.`,
    summary: 'Cap reached',
  }
}

export function costCapToastMessage(info, whenText) {
  if (info?.scope === 'global') {
    return {
      message: `Service daily budget reached. Resets at ${whenText}.`,
      summary: 'Service budget reached',
    }
  }

  return {
    message: `Daily cost limit reached ($${info.used_usd} / $${info.hard_cap_usd}). Resets at ${whenText}.`,
    summary: 'Cost cap reached',
  }
}
