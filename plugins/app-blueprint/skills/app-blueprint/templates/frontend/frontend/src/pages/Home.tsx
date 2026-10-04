{{#db}}
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import {
  createNoteMutation,
  deleteNoteMutation,
  listNotesOptions,
  listNotesQueryKey,
} from '@/client/@tanstack/react-query.gen'
import { errorMessage } from '@/lib/api'

/** The scaffold's example screen: a list from the API and a form that changes it. Replace with the app's own. */
export function Home() {
  const qc = useQueryClient()
  const notes = useQuery(listNotesOptions())
  const refresh = () => qc.invalidateQueries({ queryKey: listNotesQueryKey() })
  const onError = (err: unknown) => toast.error(errorMessage(err))
  const create = useMutation({ ...createNoteMutation(), onSuccess: refresh, onError })
  const remove = useMutation({ ...deleteNoteMutation(), onSuccess: refresh, onError })
  const [title, setTitle] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate({ body: { title, body: '' } }, { onSuccess: () => setTitle('') })
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">Notes</h1>
      <form onSubmit={submit} className="flex gap-2">
        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="A new note" />
        <button className="btn-primary" disabled={!title.trim() || create.isPending}>
          Add
        </button>
      </form>
      {notes.isPending && <p className="text-fg-muted">Loading…</p>}
      {notes.isError && <p className="text-danger">{errorMessage(notes.error)}</p>}
      {notes.data?.length === 0 && <p className="text-fg-muted">No notes yet.</p>}
      <ul className="space-y-2">
        {notes.data?.map((note) => (
          <li key={note.id} className="card flex items-center justify-between py-2">
            <span>{note.title}</span>
            <button className="btn-ghost p-1.5" onClick={() => remove.mutate({ path: { note_id: note.id } })} aria-label={`Delete ${note.title}`}>
              <Trash2 className="size-4" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
{{/db}}
{{^db}}
export function Home() {
  return (
    <div className="mx-auto max-w-2xl space-y-2">
      <h1 className="text-xl font-semibold">{{title}}</h1>
      <p className="text-fg-muted">Replace this page with the app's first screen.</p>
    </div>
  )
}
{{/db}}
