import { useState } from 'react'
import { Link } from 'react-router-dom'
import VolumeExplorer from '@/components/labs/VolumeExplorer'
import '@/styles/math-pilot.css'

export default function MathDiscovery() {
  const [layers, setLayers] = useState(2)
  const [message, setMessage] = useState('')
  const share = async () => {
    const url = `${window.location.origin}/discover/volume`
    try {
      if (navigator.share) await navigator.share({ title: 'Explore volume with SashaInfinity', text: 'Can you explain why doubling height doubles volume? Try this cube activity.', url })
      else { await navigator.clipboard.writeText(url); setMessage('Activity link copied. No learner data is included.') }
    } catch { setMessage('Sharing was cancelled or unavailable. You can copy the address from your browser.') }
  }
  return <main className="sasha-math-page min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-100 px-5 py-12 text-orange-950">
    <div className="mx-auto max-w-5xl">
      <Link to="/" className="font-bold tracking-wide">SashaInfinity · Meiporul</Link>
      <div className="mt-12 grid gap-10 md:grid-cols-2 md:items-center">
        <section><p className="text-sm font-semibold uppercase tracking-widest text-orange-700">Small discovery. Real curiosity.</p>
          <h1 className="my-5 text-4xl font-bold leading-tight md:text-5xl">Don’t just remember volume.<br />See why it works.</h1>
          <p className="mb-5 text-lg">Predict first: if a box keeps the same base and doubles its height, what happens to the number of cubes inside?</p>
          <p>Move the slider. Count the cubes in one layer, then count equal layers. Explain your reasoning to someone beside you.</p>
          <div className="mt-7 flex flex-wrap gap-3"><button onClick={() => void share()} className="rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 px-5 py-3 font-semibold text-white">Share this discovery</button>
            <Link to="/math-pilot" className="rounded-xl border border-orange-300 px-5 py-3 font-semibold">My classroom activity</Link></div>
          <p role="status" className="mt-3 text-sm">{message}</p>
        </section><VolumeExplorer layers={layers} onChange={setLayers} />
      </div>
      <section className="mt-12 grid gap-4 md:grid-cols-3">{[
        ['Predict', 'Make a prediction before moving the layers.'], ['Explain', 'Describe what stays constant and what changes.'], ['Check later', 'Classroom activities add independent questions and a delayed check.'],
      ].map(([title, text]) => <div key={title} className="rounded-2xl border border-orange-100 bg-white p-5"><h2 className="font-bold">{title}</h2><p className="mt-2 text-sm">{text}</p></div>)}</section>
      <p className="mt-8 text-sm text-orange-800">This explorer does not submit learning answers or scores. Sharing is optional and contains no student identity or results. This is a learning demonstration, not proof of mastery or improved outcomes.</p>
    </div>
  </main>
}
