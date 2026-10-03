// Saves `data` as a pretty-printed JSON file through a temporary object URL
// and <a download> click. The anchor is attached for the click (Firefox
// ignores clicks on detached anchors) and the URL is revoked on the next
// tick, not synchronously, so the download has started before the blob goes.
export function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
