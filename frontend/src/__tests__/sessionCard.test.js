import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  stripAutoPrefix,
  cardMeta,
  cardStory,
  cardChips,
  cleanPreview,
} from '@/utils/sessionCard.js'

const active = (over = {}) => ({
  id: 's',
  topic: 'Bio',
  created_at: '2026-06-01T00:00:00Z',
  ended_at: null,
  message_count: 0,
  last_activity_at: null,
  last_message_preview: null,
  progress: { focus_target_gap: null, mastered_count: 0 },
  ...over,
})

afterEach(() => vi.useRealTimers())

describe('stripAutoPrefix', () => {
  it('removes a leading [auto] marker', () => {
    expect(stripAutoPrefix('[auto] Recap of cells')).toBe('Recap of cells')
  })
  it('passes through plain text and null', () => {
    expect(stripAutoPrefix('hello')).toBe('hello')
    expect(stripAutoPrefix(null)).toBe('')
  })
})

describe('cardMeta', () => {
  it('pluralizes messages and includes last-active', () => {
    const s = active({ message_count: 3, last_activity_at: '2026-06-01T00:00:00Z' })
    expect(cardMeta(s)).toMatch(/^3 messages · last active /)
  })
  it('singular message; falls back to created_at when no activity', () => {
    const s = active({ message_count: 1, last_activity_at: null })
    expect(cardMeta(s)).toMatch(/^1 message · last active /)
  })
  it('omits the activity clause when no timestamp at all', () => {
    const s = active({ message_count: 0, created_at: null, last_activity_at: null })
    expect(cardMeta(s)).toBe('0 messages')
  })
})

describe('cardStory', () => {
  it('active: returns the trimmed preview', () => {
    const s = active({ last_message_preview: '  What is ATP?  ' })
    expect(cardStory(s)).toBe('What is ATP?')
  })

  it('active: empty string when no preview — focus and mastery do NOT leak in', () => {
    const s = active({ progress: { focus_target_gap: 'ATP yield', mastered_count: 3 } })
    expect(cardStory(s)).toBe('')
  })

  it('ended: summary with [auto] stripped; Completed fallback', () => {
    const ended = active({
      ended_at: '2026-06-02T00:00:00Z',
      last_session_summary: '[auto] Covered the Krebs cycle',
    })

    expect(cardStory(ended)).toBe('Covered the Krebs cycle')
    const bare = active({ ended_at: '2026-06-02T00:00:00Z', last_session_summary: null })
    expect(cardStory(bare)).toBe('Completed')
  })
})

describe('cleanPreview', () => {
  it('replaces display and inline math with [formula]', () => {
    expect(cleanPreview('Solve $$x = \\frac{-b}{2a}$$ then $y^2$ next')).toBe(
      'Solve [formula] then [formula] next',
    )
  })
  it('passes through plain text and null', () => {
    expect(cleanPreview('hello there')).toBe('hello there')
    expect(cleanPreview(null)).toBe('')
  })

  it('strips bold markers but keeps the words', () => {
    expect(cleanPreview('Routers forward **IP addresses** onward')).toBe(
      'Routers forward IP addresses onward',
    )
    expect(cleanPreview('Routers forward __IP addresses__ onward')).toBe(
      'Routers forward IP addresses onward',
    )
  })

  it('strips italic markers but keeps the words', () => {
    expect(cleanPreview('A *subtle* hint')).toBe('A subtle hint')
    expect(cleanPreview('A _subtle_ hint')).toBe('A subtle hint')
  })

  it('strips inline code backticks and strikethrough', () => {
    expect(cleanPreview('Call `render()` first')).toBe('Call render() first')
    expect(cleanPreview('Not ~~wrong~~ right')).toBe('Not wrong right')
  })

  it('keeps link and image text, drops the target', () => {
    expect(cleanPreview('See [the RFC](https://example.com/rfc) for detail')).toBe(
      'See the RFC for detail',
    )
    expect(cleanPreview('Here ![a diagram](/img/d.png) sits')).toBe('Here a diagram sits')
  })

  it('strips heading, list and blockquote markers at line start', () => {
    expect(cleanPreview('# Subnetting\n- masks\n* hosts\n1. gateways\n> a note')).toBe(
      'Subnetting masks hosts gateways a note',
    )
  })

  it('leaves word-internal underscores alone', () => {
    expect(cleanPreview('Rename snake_case to camelCase')).toBe('Rename snake_case to camelCase')
    expect(cleanPreview('Both snake_case and _emphasis_ here')).toBe(
      'Both snake_case and emphasis here',
    )
  })
})

describe('cardStory (active)', () => {
  it('falls back to the summary when the preview is very short', () => {
    expect(
      cardStory(
        active({ last_message_preview: 'okay', last_session_summary: '[auto] Covered routers.' }),
      ),
    ).toBe('Covered routers.')
  })
  it('keeps a short preview when there is no summary', () => {
    expect(cardStory(active({ last_message_preview: 'okay' }))).toBe('okay')
  })
  it('cleans math out of the preview', () => {
    expect(cardStory(active({ last_message_preview: 'Here: $$a^2+b^2=c^2$$' }))).toBe(
      'Here: [formula]',
    )
  })
})

describe('cardChips', () => {
  it('returns focus then mastered when both present', () => {
    const s = active({ progress: { focus_target_gap: 'ATP yield', mastered_count: 2 } })
    expect(cardChips(s)).toEqual([
      { type: 'focus', label: 'ATP yield' },
      { type: 'mastered', label: '2 mastered', count: 2 },
    ])
  })

  it('omits the mastered chip at zero and the focus chip when null', () => {
    expect(cardChips(active())).toEqual([])
    expect(cardChips(active({ progress: { focus_target_gap: null, mastered_count: 1 } }))).toEqual([
      { type: 'mastered', label: '1 mastered', count: 1 },
    ])
  })

  it('handles null progress safely', () => {
    expect(cardChips(active({ progress: null }))).toEqual([])
  })

  it('includes a level chip, ordered focus then level then mastered', () => {
    const s = active({
      progress: { focus_target_gap: 'ATP yield', level: 'intermediate', mastered_count: 2 },
    })

    expect(cardChips(s)).toEqual([
      { type: 'focus', label: 'ATP yield' },
      { type: 'level', label: 'Intermediate', level: 'intermediate' },
      { type: 'mastered', label: '2 mastered', count: 2 },
    ])
  })

  it('omits the level chip when level is null', () => {
    expect(
      cardChips(active({ progress: { focus_target_gap: null, level: null, mastered_count: 0 } })),
    ).toEqual([])
  })
})
