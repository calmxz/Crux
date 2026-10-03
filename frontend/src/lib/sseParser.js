function tryParseJSON(s) {
  try {
    return JSON.parse(s)
  } catch {
    return s
  }
}

export async function parseSSEStream(stream, onEvent, { signal } = {}) {
  const reader = stream.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  if (signal) {
    signal.addEventListener('abort', () => {
      reader.cancel(new Error('aborted')).catch(() => {})
    })
  }

  try {
    while (true) {
      const { done, value } = await reader.read()

      // Check abort BEFORE handling done — reader.cancel() resolves with done:true,
      // so we must re-throw here to convert that silent resolution into a rejection.
      if (signal?.aborted) throw new Error('aborted')

      if (done) {
        if (buffer.trim()) flushFrame(buffer, onEvent)

        return
      }

      buffer += decoder.decode(value, { stream: true })
      let sep

      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        flushFrame(frame, onEvent)
      }
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
      /* already released */
    }
  }
}

function flushFrame(frame, onEvent) {
  let eventName = 'message'
  const dataLines = []

  for (const line of frame.split('\n')) {
    if (line.startsWith(':')) continue

    if (line.startsWith('event:')) eventName = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }

  if (!dataLines.length) return
  const joined = dataLines.join('\n')
  onEvent({ event: eventName, data: tryParseJSON(joined) })
}
