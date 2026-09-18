import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { Segment } from "../../api/management"
import { SEGMENTS } from "./labels"

/** Estado del cliente: icono + texto, nunca solo el color. */
export default function SegmentBadge({ segment }: { segment: Segment }) {
  const s = SEGMENTS[segment]
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-semibold text-slate-700">
      <FontAwesomeIcon icon={s.icon} style={{ color: s.color }} className="text-[11px]" />
      {s.one}
    </span>
  )
}
