import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UploadStatus from '@/components/chat/UploadStatus.vue'

describe('UploadStatus', () => {
  it('renders nothing when upload is null', () => {
    const wrapper = mount(UploadStatus, { props: { upload: null } })
    expect(wrapper.html().trim()).toBe('<!--v-if-->')
  })

  it('pending: renders testid and text', () => {
    const wrapper = mount(UploadStatus, {
      props: { upload: { kind: 'pending', text: 'Uploading doc.pdf…' } },
    })

    const el = wrapper.find('[data-testid="upload-status-pending"]')
    expect(el.exists()).toBe(true)
    expect(el.text()).toContain('Uploading doc.pdf')
  })

  it('ready: renders testid, correct class, and text', () => {
    const wrapper = mount(UploadStatus, {
      props: { upload: { kind: 'ready', text: 'doc.pdf is ready.' } },
    })

    const el = wrapper.find('[data-testid="upload-status-ready"]')
    expect(el.exists()).toBe(true)
    expect(el.classes()).toContain('upload-status-ready')
    expect(el.text()).toContain('ready')
  })

  it('failed: renders testid, correct class, and text', () => {
    const wrapper = mount(UploadStatus, {
      props: { upload: { kind: 'failed', text: 'Upload failed: too big' } },
    })

    const el = wrapper.find('[data-testid="upload-status-failed"]')
    expect(el.exists()).toBe(true)
    expect(el.classes()).toContain('upload-status-failed')
    expect(el.text()).toContain('too big')
  })

  it('is a polite live region so screen readers hear ingestion status (WCAG 4.1.3)', () => {
    const wrapper = mount(UploadStatus, {
      props: { upload: { kind: 'ready', text: 'doc.pdf is ready.' } },
    })

    const el = wrapper.find('[data-testid="upload-status-ready"]')
    expect(el.attributes('role')).toBe('status')
    expect(el.attributes('aria-live')).toBe('polite')
    expect(el.attributes('aria-atomic')).toBe('true')
  })
})
