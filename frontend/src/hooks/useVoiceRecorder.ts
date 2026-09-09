import { useCallback, useRef, useState } from "react"

/** Graba la voz del alumno y devuelve un WAV listo para evaluar.
 *
 * Por qué WAV y no lo que da MediaRecorder tal cual: el navegador graba
 * en webm/opus (o mp4 en Safari), y convertirlo en el servidor exigiría
 * ffmpeg en la imagen del backend. Aquí el propio navegador ya trae un
 * decodificador de audio completo (`decodeAudioData`), así que se decodifica
 * y se re-encoda a WAV en el cliente: cero dependencias nuevas en el
 * servidor y un formato único que el evaluador entiende siempre, venga de
 * Chrome, Firefox o Safari.
 *
 * Se remuestrea a 16 kHz mono porque es el estándar de los modelos de voz
 * y recorta el envío: una frase de 3s pasa de ~500KB a ~96KB, que en el
 * móvil de un alumno con datos limitados importa.
 */
const TARGET_SAMPLE_RATE = 16000

export type RecorderState = "idle" | "recording" | "processing" | "denied"

export function useVoiceRecorder() {
  const [state, setState] = useState<RecorderState>("idle")
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const resolveRef = useRef<((wav: Blob | null) => void) | null>(null)

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = async () => {
        // Se sueltan los micrófonos SIEMPRE: si no, el navegador deja el
        // indicador de "grabando" encendido y el alumno cree, con razón,
        // que le seguimos escuchando.
        stream.getTracks().forEach((track) => track.stop())
        setState("processing")
        const wav = await toWav(new Blob(chunksRef.current))
        setState("idle")
        resolveRef.current?.(wav)
        resolveRef.current = null
      }

      recorder.start()
      recorderRef.current = recorder
      setState("recording")
      return true
    } catch {
      // Cubre tanto el rechazo del permiso como no tener micrófono.
      setState("denied")
      return false
    }
  }, [])

  const stop = useCallback(
    () =>
      new Promise<Blob | null>((resolve) => {
        const recorder = recorderRef.current
        if (!recorder || recorder.state === "inactive") return resolve(null)
        resolveRef.current = resolve
        recorder.stop()
      }),
    [],
  )

  return { state, start, stop }
}

async function toWav(blob: Blob): Promise<Blob | null> {
  try {
    const context = new AudioContext()
    const decoded = await context.decodeAudioData(await blob.arrayBuffer())
    await context.close()

    // OfflineAudioContext remuestrea con el resampler nativo del
    // navegador — mejor que interpolar a mano en JS, y sin código propio
    // que mantener.
    const frames = Math.ceil(decoded.duration * TARGET_SAMPLE_RATE)
    const offline = new OfflineAudioContext(1, frames, TARGET_SAMPLE_RATE)
    const source = offline.createBufferSource()
    source.buffer = decoded
    source.connect(offline.destination)
    source.start()
    return encodeWav(await offline.startRendering())
  } catch {
    return null
  }
}

function encodeWav(buffer: AudioBuffer): Blob {
  const samples = buffer.getChannelData(0)
  const bytes = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(bytes)

  const writeText = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i))
  }

  writeText(0, "RIFF")
  view.setUint32(4, 36 + samples.length * 2, true)
  writeText(8, "WAVEfmt ")
  view.setUint32(16, 16, true) // tamaño del bloque fmt
  view.setUint16(20, 1, true) // PCM sin comprimir
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, TARGET_SAMPLE_RATE, true)
  view.setUint32(28, TARGET_SAMPLE_RATE * 2, true) // bytes por segundo
  view.setUint16(32, 2, true) // alineación de bloque
  view.setUint16(34, 16, true) // bits por muestra
  writeText(36, "data")
  view.setUint32(40, samples.length * 2, true)

  // Float [-1,1] a PCM de 16 bits con signo. El acotado no es cosmético:
  // una muestra por encima de 1.0 (pasa al grabar pegado al micrófono)
  // desbordaría el entero y sonaría como un chasquido.
  let offset = 44
  for (const sample of samples) {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
    offset += 2
  }

  return new Blob([bytes], { type: "audio/wav" })
}
