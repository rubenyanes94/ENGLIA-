import {
  faBackward,
  faForward,
  faGaugeHigh,
  faHeadphones,
  faPause,
  faPlay,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useRef, useState } from "react"
import { API_URL } from "../api/client"
import type { LessonDetail } from "../api/types"

// Velocidades pensadas para aprender un idioma, no para consumir un
// podcast: 0.75 para descomponer una frase inglesa que va muy rápida,
// 1.25 para repasar algo ya sabido. Nada por encima de 1.5 — a esa
// velocidad la pronunciación deja de ser un modelo útil.
const SPEEDS = [0.75, 1, 1.25, 1.5]

const SKIP_SECONDS = 10

/** Divide el guión en fragmentos, marcando cuáles son inglés (los que el
 * guión encierra entre [[dobles corchetes]] para que Piper los narre con
 * la voz inglesa — ver backend/app/media/piper_tts.py). En la
 * transcripción se resaltan: el alumno ve de un vistazo qué tiene que
 * repetir, en vez de leer un muro de texto bilingüe indiferenciado. */
function parseScript(script: string): { text: string; english: boolean }[] {
  const parts: { text: string; english: boolean }[] = []
  const pattern = /\[\[(.+?)\]\]/gs
  let cursor = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(script)) !== null) {
    const before = script.slice(cursor, match.index)
    if (before) parts.push({ text: before, english: false })
    parts.push({ text: match[1], english: true })
    cursor = match.index + match[0].length
  }
  const tail = script.slice(cursor)
  if (tail) parts.push({ text: tail, english: false })
  return parts
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0:00"
  const minutes = Math.floor(seconds / 60)
  const rest = Math.floor(seconds % 60)
  return `${minutes}:${rest.toString().padStart(2, "0")}`
}

export default function AudioLesson({ lesson }: { lesson: LessonDetail }) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(lesson.audio_duration_seconds ?? 0)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    // Al cambiar de lección, el <audio> se reinicia pero el estado local
    // no — sin esto, la barra se quedaría con el tiempo de la anterior.
    setPlaying(false)
    setCurrent(0)
    setDuration(lesson.audio_duration_seconds ?? 0)
  }, [lesson.id, lesson.audio_duration_seconds])

  if (!lesson.audio_url) return null

  function toggle() {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      void audio.play()
    } else {
      audio.pause()
    }
  }

  function skip(seconds: number) {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = Math.min(Math.max(audio.currentTime + seconds, 0), audio.duration || 0)
  }

  function cycleSpeed() {
    const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]
    setSpeed(next)
    if (audioRef.current) audioRef.current.playbackRate = next
  }

  function seek(event: React.MouseEvent<HTMLDivElement>) {
    const audio = audioRef.current
    if (!audio || !duration) return
    const bounds = event.currentTarget.getBoundingClientRect()
    audio.currentTime = ((event.clientX - bounds.left) / bounds.width) * duration
  }

  const progress = duration ? (current / duration) * 100 : 0

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      {/* Reproductor */}
      <div className="relative bg-slate-900 p-6 text-white sm:p-8">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-blue-500/20 blur-3xl"
        />
        <div className="relative">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-300">
            <FontAwesomeIcon icon={faHeadphones} /> Lección narrada
          </p>
          <h3 className="mt-2 text-xl font-extrabold tracking-tight">{lesson.title}</h3>

          <div className="mt-6 flex items-center gap-4">
            <button
              onClick={toggle}
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xl text-white shadow-lg shadow-blue-600/30 transition active:scale-95 hover:bg-blue-500"
              aria-label={playing ? "Pausar" : "Reproducir"}
            >
              <FontAwesomeIcon icon={playing ? faPause : faPlay} className={playing ? "" : "ml-1"} />
            </button>

            <div className="min-w-0 flex-1">
              <div
                onClick={seek}
                className="group h-2.5 w-full cursor-pointer overflow-hidden rounded-full bg-white/15"
                role="progressbar"
                aria-valuenow={Math.round(progress)}
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-400 to-sky-300 transition-[width] duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between font-mono text-xs text-slate-400">
                <span>{formatTime(current)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <ControlButton onClick={() => skip(-SKIP_SECONDS)} icon={faBackward} label={`-${SKIP_SECONDS}s`} />
            <ControlButton onClick={() => skip(SKIP_SECONDS)} icon={faForward} label={`+${SKIP_SECONDS}s`} />
            <ControlButton onClick={cycleSpeed} icon={faGaugeHigh} label={`${speed}×`} />
            <span className="ml-auto text-[11px] text-slate-400">
              Baja la velocidad para repetir las frases en inglés
            </span>
          </div>

          <audio
            ref={audioRef}
            src={`${API_URL}${lesson.audio_url}`}
            preload="metadata"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
            // La duración de la BD es una estimación del pipeline; la real
            // la sabe el navegador al leer los metadatos del archivo.
            onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          />
        </div>
      </div>

      {/* Transcripción */}
      {lesson.script && (
        <div className="p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Transcripción</p>
          <p className="mt-3 leading-relaxed text-slate-700">
            {parseScript(lesson.script).map((part, i) =>
              part.english ? (
                <strong
                  key={i}
                  className="mx-0.5 rounded-md bg-blue-50 px-1.5 py-0.5 font-semibold text-blue-700"
                >
                  {part.text}
                </strong>
              ) : (
                <span key={i}>{part.text}</span>
              ),
            )}
          </p>
          <p className="mt-4 text-xs text-slate-400">
            En azul, lo que se dice en inglés — es lo que tienes que repetir en voz alta.
          </p>
        </div>
      )}
    </section>
  )
}

function ControlButton({
  onClick,
  icon,
  label,
}: {
  onClick: () => void
  icon: typeof faPlay
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 rounded-full bg-white/10 px-3.5 py-2 text-xs font-semibold text-slate-200 transition active:scale-95 hover:bg-white/20"
    >
      <FontAwesomeIcon icon={icon} className="text-[10px]" />
      {label}
    </button>
  )
}
