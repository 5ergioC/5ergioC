# tools

Generadores de los assets del README. Todo se ejecuta desde la raíz del repo.

`build_card.py` solo usa la stdlib y corre en CI. Los demás son locales:
necesitan Pillow (`pip install pillow`) y tipografías de Windows.

| Script | Genera | Cuándo correrlo |
|---|---|---|
| `palette.py` | nada, es la fuente de colores | Al cambiar de tema |
| `build_greeting.py` | `Images/greeting-{dark,light}.svg` | Al cambiar el saludo |
| `preview.py` | `preview.html` | Antes de commitear cualquier cambio |
| `cutout.py` | `tools/face-cut.png` | Al cambiar la foto o el encuadre |
| `photo2ascii.py` | `tools/portrait-{dark,light}.txt` | Después de `cutout.py` |
| `build_portrait.py` | `Images/portrait-{dark,light}.svg` | Después de `photo2ascii.py` |
| `build_card.py` | `Images/whoami-{dark,light}.svg` | A diario en Actions, o tras editar los campos |
| `build_comic.py` | `Images/interests-{dark,light}.png` | Al cambiar la frase en Comic Sans |
| `build_sheikah.py` | `Images/sheikah-{dark,light}.svg` | Cuando tengas la fuente Sheikah |
| `build_quote.py` | `Images/quote-{dark,light}.svg` | Al cambiar la frase de cierre (necesita `pyfiglet`) |
| `build_goodbye.py` | `Images/Goodbye.png` | Al cambiar el GIF fuente |

## Ver antes de commitear

```bash
python tools/preview.py --open
```

Saca los dos temas lado a lado. GitHub elige uno según el tema del visitante,
así que un navegador solo enseña la mitad: esta es la única forma de cachar una
pieza que se ve bien en oscuro y desaparece en claro.

La lista de imágenes sale del propio `README.md`, no de una lista aparte, así
que una pieza nueva aparece en el previo sin tocar el script. Los bloques
comentados se ignoran: si no están en la página, no están en el previo.

## Cambiar de paleta

Todos los colores salen de `tools/palette.py`. Cambia `ACTIVE`, vuelve a correr
los scripts y la página entera se mueve junta:

```bash
python tools/palette.py --list
python tools/build_card.py && python tools/build_portrait.py && python tools/build_greeting.py
python tools/build_comic.py && python tools/build_sheikah.py && python tools/build_quote.py
```

Hay tres: `green` (el fósforo original), `purple` (el activo) y `amber`.

Los nombres son roles, no colores, así que una paleta nueva no obliga a
renombrar nada: `bg`, `border`, `head`, `key`, `value`, `dim`, `accent`, `ink`.
En `purple` son tres tonos haciendo tres trabajos —morado para etiquetas,
magenta para las reglas de sección, cian para los números— y por eso la
tarjeta se lee de un vistazo en vez de ser un muro de un solo color.

La serpiente la dibuja una GitHub Action, no estos scripts, así que sus
colores serían un segundo sitio que acordarse de editar. El workflow llama a
`python tools/palette.py --snake` y usa lo que salga.

## Cambiar la cara

Deja la foto en `tools/face.jpg` (o `.png`) y corre:

```bash
python tools/photo2ascii.py tools/face.jpg --width 104 --levels 4 --crop 360,95,670,480 --gamma 0.55 --oval --sharpen --dither --invert
python tools/build_portrait.py
```

`tools/face*` está gitignorado: solo se commitean las dos `portrait-*.txt` y
los SVG, así que la foto original nunca llega al repo público.

Ese comando no es capricho; cada bandera arregla algo que sin ella rompe el
retrato. En orden de importancia:

- `--dither` es lo único que hace legible una fotografía a este tamaño.
  Cuantizar de golpe borra los rasgos; difundir el error cambia precisión
  tonal por detalle aparente, igual que un tramado de periódico. Sin esto no
  hay retrato, solo una mancha.
- `--levels 4`. Diez tonos de una cara a esta resolución se empastan.
- `--crop`. Una foto de alguien en un cuarto es, sobre todo, cuarto.
- `--oval` desvanece las esquinas a blanco y, con `--invert`, el blanco es el
  extremo vacío de la rampa: el cuarto desaparece en vez de volverse tinta.
- `--gamma 0.55` sube los medios tonos. La luz de interior deja la piel en
  mitad del rango, donde todos los glifos se parecen; esto la manda al extremo
  ralo y deja pelo, ojos y boca como las únicas marcas densas.

Los números del `--crop` son de *esta* foto. Con otra hay que volver a
ajustarlos: encuadra la cara con poco margen.

**Una lámina por tema, y la polaridad ya no es una bandera.** La tinta sobre
papel es oscura, así que en modo claro los glifos tienen que caer sobre las
sombras y la página se asoma como piel. La tinta en una terminal es luz, así
que sobre negro los glifos tienen que caer sobre las zonas iluminadas y el
panel se asoma como sombra. Poner una lámina sobre el fondo equivocado la
convierte en un negativo: sólida donde debería estar vacía, y tan tenue que
casi desaparece.

Por eso `photo2ascii.py` escribe `portrait-dark.txt` y `portrait-light.txt` de
una sola corrida, y `build_portrait.py` toma la que corresponde. No hay
`--invert` que equivocar.

Tampoco `--levels` ni `--dither` aquí. Con la rampa completa de diez tonos y
sin tramar, el degradado sale suave y se parece más al arte que hace
[andriidrok1](https://github.com/andriidrok1/andriidrok1). El tramado hace
falta cuando se recorta a cuatro tonos; con diez, solo añade ruido.

`RAMPED` en `build_portrait.py` decide, por tema, si los glifos llevan además
una rampa de brillo o van todos en una sola tinta. Está en rampa para oscuro
—es lo que modela la cara y hace que los rasgos se lean sobre negro— y en
monocromo para claro, donde una sola tinta da una figura más firme. Elegido a
ojo comparando las cuatro combinaciones, no deducido.

### La ruta buena: quitar el fondo de verdad

`--oval` es un instrumento romo: una elipse se queda con lo que caiga dentro,
que en esta foto incluía parte de la silla y la cortina. `cutout.py` recorta
el sujeto con segmentación real:

```bash
python tools/cutout.py tools/face.jpg --crop 418,347,1216,1500
python tools/photo2ascii.py tools/face-cut.png --width 104 --trim --gamma 0.55 --sharpen
python tools/build_portrait.py
```

El `--crop` de `cutout.py` es lo que decide cuánto de ti entra. Encuadres
probados sobre esta foto:

| Encuadre | `--crop` | Resultado |
|---|---|---|
| Medio cuerpo | `418,347,1216,1500` | **el activo**. 600x883 |
| Cabeza | `590,350,950,760` | los rasgos se leen, pero es mucha cara |
| Cabeza + hombros | `450,350,1120,1180` | intermedio |
| Figura completa | *(sin `--crop`)* | se lee la pose, cara muy chica |

Los números son de la foto de 1500x2000. La resolución es lo que decide si un
recorte cerrado funciona: con la versión de 400x400 de la misma foto, la cabeza
sola dejaba ~100 px de fuente y no daba para 104 columnas.

Más cara significa mejores rasgos: la rampa tiene cuatro tonos, y lo que no
cabe en cuatro tonos no se ve. Después ya no hacen falta ni
`--oval` ni `--crop`: el alfa es la máscara y `--trim` recorta a lo que el
recorte realmente cubre, así el sujeto llena el marco en vez de flotar en el
margen con el que se exportó.

Corre **en local**. Los quitafondos en línea piden subir la foto, que es mal
trato por una imagen de tu propia cara. La primera corrida baja un modelo de
~176 MB a `~/.u2net` y de ahí en adelante funciona sin red.

`rembg` es pesado (onnxruntime, numba, scikit-image) y solo lo necesita este
script, por eso no se importa en ningún otro sitio de `tools/`:

```bash
pip install "rembg[cpu]"
```

Si prefieres recortarte a mano en Photoshop o Figma, exporta PNG con alfa y
sáltate `cutout.py`: `photo2ascii.py` usa cualquier canal alfa que encuentre.

### Qué foto pedir

| | |
|---|---|
| Relación de aspecto | **4:5 vertical** (la actual). Cuadrada también sirve |
| Resolución | cualquiera desde ~900 px de lado largo; se reduce a 104x65 celdas |
| Encuadre | cabeza y hombros: el pelo casi tocando el borde superior, el mentón sobre el 70-75 % de la altura |
| Ancho de la cara | 55-65 % del ancho del cuadro |
| Luz | una fuente clara y lateral. La luz difusa de interior aplana los rasgos, que es justo lo que la rampa necesita para separarlos |
| Fondo | liso, y con brillo distinto al de la piel |

El ancho del SVG es fijo en 600 px, así que la relación de aspecto de la foto
decide el alto de la tarjeta: 4:5 da 600x737, cuadrada da 600x602.

Ninguna bandera arregla que la piel y el fondo tengan el mismo brillo.

La foto ideal es vertical, con la cara grande y el fondo limpio: el conversor
solo tiene diez niveles de gris, así que un fondo con detalle se vuelve ruido.
`--invert` si la foto es clara sobre fondo oscuro; `--contrast 1.8` marca más
los rasgos.

El ancho controla el tamaño del recuadro. 52 columnas dan unos 440 px, que es
lo que pide el README. Pasar de ~70 hace la tarjeta más ancha que la de WHOAMI.

La animación es SMIL puro: cada fila se abre con un barrido de izquierda a
derecha, y el escalonado de los arranques convierte eso en un solo borde
diagonal cruzando la lámina, como una terminal imprimiendo la imagen. Encima
corre una banda de scanline en bucle y un parpadeo leve.

Cada fila va fijada con `textLength` a su propio número de caracteres, así que
la geometría es exacta en vez de una apuesta sobre el avance de la
monoespaciada del visitante.
El proxy camo de GitHub quita los scripts de los SVG pero deja pasar SMIL: es
lo mismo que hace funcionar a la serpiente. Un `<img>` no recibe hoja de
estilos, así que no hay forma de respetar `prefers-reduced-motion`; por eso el
movimiento es lento y de bajo contraste a propósito.

## Cambiar los datos de la tarjeta

Los campos están en la lista `lines` dentro de `build()`, en `build_card.py`.
`Uptime` es la edad, calculada desde `BIRTH_YEAR`, que guarda **solo el año**.
Una fecha de nacimiento exacta es justo el dato con el que se arman las
preguntas de recuperación de cuenta, y esto vive en un repo público. Guardar
solo el año hace que la edad cambie el 1 de enero en vez del cumpleaños, que
es el punto: nada en la página insinúa el mes. El costo es leer un año de más
entre año nuevo y el cumpleaños real.

Los conteos salen de la API de GitHub.

Dos detalles de esos conteos:

- `SKIP_LINE_COUNTS` excluye repos cuyo diff es data o bundles, no código
  escrito. `Reto-Capa-de-Datos` (+3,523,160 / −0) y `5ergioC.github.io`
  (+499,054) son el 87 % de las líneas atribuidas a la cuenta. Quita un nombre
  del conjunto para volver a contarlo.
- La búsqueda de commits lleva `is:public`. Sin eso el número sube o baja según
  los repos privados que alcance a ver el token del momento, y la tarjeta daría
  una cifra distinta en cada corrida.

`tools/stats-cache.json` guarda la última respuesta buena. Si la API falla o
se agota el límite, el build usa el caché en vez de romperse.

## La línea en Sheikah

dcode.fr no tiene tipografía. Compone la línea con un PNG de 36x36 por
carácter bajo `/tools/sheikah/images/char(NN).png`, uno por código ASCII, así
que lo único que se puede sacar de ahí es una captura.

`build_sheikah.py` lee un `.ttf` de verdad y convierte cada glifo a un `<path>`
de SVG. El resultado no depende de que el visitante tenga la fuente, y la
fuente no hace falta commitearla: apunta `--font` a donde la tengas.

El fan-font de referencia es el de Sarinilli en DeviantArt, gratis para uso no
comercial. Los glifos son de Nintendo (Breath of the Wild): está bien para un
perfil personal, no para nada que se venda.

```bash
python tools/build_sheikah.py --font ~/Downloads/sheikah.ttf
```

Si la fuente mapea solo mayúsculas o solo minúsculas, el script prueba las dos
y avisa por consola de cualquier carácter que no encuentre.

El corte de línea sale de la lista `LINES`: una entrada por renglón, centradas
entre sí. En una sola línea los 34 caracteres quedaban más anchos que la página.

El `viewBox` se mide de la tinta real, no del ascendente declarado. *Handwritten
Sheikah Runes* dice tener un ascendente de 792 unidades y ningún glifo pasa de
537: sin medirlo, un tercio de la imagen sería relleno vacío.

## Tamaño del texto

El saludo, la frase en Comic Sans y la línea Sheikah comparten
`TEXT_HEIGHT = 24` en `palette.py`: la altura de una mayúscula, en píxeles ya
mostrados. Cada generador la convierte a tamaño de fuente con las proporciones
de su propia tipografía, porque 24 px de Consolas, de Comic Sans y de runas
Sheikah son tres tamaños de letra distintos. Antes estaban en 13, 27 y 29.

Para las runas se usa la **mediana** de la altura de cada una, no la caja que
las envuelve a todas: las runas se apoyan a alturas un poco distintas, así que
esa caja mide 13 % más que cualquier runa y las dejaba en ~21 px.

Las tres se muestran a su ancho natural en el README; reescalarlas en el HTML
rompería la igualdad y además las desenfocaría. Si cambias `TEXT_HEIGHT`,
corre los tres generadores y actualiza esos tres `width=`.

## Notas de render

- Nada de `<style>` ni scripts dentro de los SVG: camo los quitaría.
- Cada línea de la tarjeta mide exactamente `LINE_CHARS` caracteres y se estira
  a `TEXT_WIDTH` con `textLength` + `lengthAdjust="spacingAndGlyphs"`. Así llena
  el marco igual con Consolas, Menlo o DejaVu Sans Mono. Sin eso el texto se
  quedaba unos 200 px corto del borde derecho en las fuentes angostas.
  Si cambias `LINE_CHARS`, revisa que `field()`, `rule()` y `pair()` sigan
  devolviendo ese largo exacto: una línea más corta se estira de más y se nota.
- La frase de cierre sale de un figlet real (DOS Rebel, vía `pyfiglet`):
  `pip install pyfiglet`. Antes se dibujaba con Impact reducido a una rejilla,
  y eso era lo que se veía raro: a siete celdas por letra los huecos de Impact
  se cerraban y `g`, `o`, `a`, `e` salían como bultos, y la "sombra" era la
  rebanada que dejara el desplazamiento. Un figlet se dibujó a mano sobre la
  rejilla con los huecos abiertos a propósito; por eso se lee como letra.
- Cada celda se dibuja como geometría, nunca como texto: bloques sólidos
  fusionados por fila, sombras como relleno de scanlines (más ralo para `░`,
  más denso para `▓`), y trazos finos para las fuentes que dibujan la sombra
  con líneas de caja. Así no depende de que la fuente del visitante distinga
  U+2588 de U+2591, que en la monoespaciada de GitHub casi no se distinguen.
- Las celdas miden píxeles enteros (3x6), así las filas se tocan sin las
  rendijas que dejan los bordes fraccionarios. Por eso el SVG mide 744 px y no
  los 848 del máximo, y el README lo muestra a ese tamaño exacto.
- `--font` prueba otra: `ansi_shadow`, `ansi_regular`, `pagga`, `bloody` ya
  se comprobaron. DOS Rebel ganó por mayúsculas y minúsculas, legibilidad y
  porque es la del "Bye bye" que funcionó.
- `Goodbye.png` es APNG con canal alfa real. Un GIF transparente solo tiene
  1 bit de alfa y dejaría un borde blanco en cada píxel antialiado.
- El saludo y la frase en Comic Sans van sin fondo. Hornear el gris oscuro de
  GitHub habría servido para un solo tema, y se rompería el día que GitHub lo
  retoque; con alfa, las dos variantes solo cambian el color de la tinta.
- El efecto de tipeo del saludo es un `<clipPath>` cuyo ancho crece en pasos
  discretos. Los dos `<text>` llevan `textLength` fijo: sin eso el corte del
  clip no caería en los bordes de cada carácter.
