import { useState, useCallback, useEffect } from 'react'
import { api } from '../api'

export function useRecording() {
  const [session, setSession] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [draft, setDraft] = useState(null)

  const startRecording = useCallback(async (title = '', source = 'manual') => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderStart({ title, source })
      setSession(result)
      setEvents([])
      setDraft(null)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const stopRecording = useCallback(async (sessionId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderStop(sessionId)
      // Fetch events after stopping
      const evts = await api.recorderListEvents(sessionId)
      setSession(prev => prev ? { ...prev, status: result.status, event_count: result.event_count } : null)
      setEvents(evts || [])
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const cancelRecording = useCallback(async (sessionId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderCancel(sessionId)
      setSession(null)
      setEvents([])
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const recordEvent = useCallback(async (sessionId, eventData) => {
    try {
      const result = await api.recorderRecordEvent(sessionId, eventData)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  const convertToSkill = useCallback(async (sessionId, name = '', description = '') => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderConvertToSkill(sessionId, { name, description })
      setDraft(result)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const approveDraft = useCallback(async (draftId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderApproveDraft(draftId)
      setDraft(prev => prev ? { ...prev, status: result.status } : null)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const rejectDraft = useCallback(async (draftId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderRejectDraft(draftId)
      setDraft(null)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const saveAsSkill = useCallback(async (draftId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.recorderSaveAsSkill(draftId)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const checkCurrentSession = useCallback(async () => {
    try {
      const result = await api.recorderCurrent()
      if (result && result.session_id) {
        setSession(result)
        return result
      }
      return null
    } catch (err) {
      return null
    }
  }, [])

  const deleteEvent = useCallback(async (sessionId, eventId) => {
    setEvents(prev => prev.filter(e => e.id !== eventId && e.event_order !== eventId))
  }, [])

  return {
    session, events, draft, loading, error,
    startRecording, stopRecording, cancelRecording,
    recordEvent, convertToSkill, approveDraft, rejectDraft, saveAsSkill,
    checkCurrentSession, deleteEvent,
  }
}
