/** Campo de texto de las pantallas de entrada (login, registro, contraseña). */
export default function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  minLength,
  autoComplete,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  required?: boolean
  minLength?: number
  autoComplete?: string
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</span>
      <input
        type={type}
        required={required}
        minLength={minLength}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-900 outline-none ring-brand-500 focus:ring-2"
      />
    </label>
  )
}
