/** Relleno lateral común a navegación, contenido y footer.
 *
 * El contenido ocupa todo el ancho de la ventana, sin tope. Lo que evita
 * que en un monitor grande quede estirado de lado a lado es que cada
 * pantalla reparte ese ancho en columnas; las que son de lectura (perfil,
 * chat) mantienen su propio ancho máximo. Las tres franjas comparten este
 * relleno para que el logo, el contenido y el footer queden alineados. */
export const PAGE_GUTTER = "px-4 sm:px-6 lg:px-10 2xl:px-16"

// En su propio módulo y no dentro de Layout: AppFooter también lo usa, y
// Layout importa AppFooter. Importarlo desde Layout crearía un ciclo.
