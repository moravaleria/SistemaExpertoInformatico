# Sistema Experto de Diagnóstico de Fallas Informáticas

Sistema experto basado en reglas con encadenamiento hacia adelante, construido a partir del motor de inferencia. Diagnostica problemas de computadores (energía, memoria, video, disco, malware, sobrecalentamiento, drivers y red) y entrega una recomendación con su cadena de razonamiento.


## Qué hace (requisitos del taller)


Base de conocimiento desde archivo externo  `conocimiento/base_conocimiento_informatica.json` (formato JSON, ver más abajo) 
Estrategia de resolución de conflictos con referentes Sección *Estrategia de resolución de conflictos* y `sistema_experto/motor.py` 
 Hechos iniciales desde archivo o por interacción  `.txt`/`.json` en `casos/`, preguntas por consola (`--interactivo`) o casillas en la GUI 
Interfaz simple, resultados paso a paso GUI en Tkinter (botón *Siguiente paso*) y CLI (`--paso-a-paso`) 
Recomendación del sistema experto  Panel «Recomendación» / sección final de la CLI, con cadena de razonamiento 
Caso de informática, ≥ 15 reglas, con encadenamiento **39 reglas**, cadenas de hasta **3 niveles** (síntoma → intermedio → diagnóstico → recomendación)

## Instalación y dependencias

* Python **3.9 o superior**.
* **Sin dependencias externas** (solo biblioteca estándar). La GUI usa Tkinter, que viene con Python
  (en Linux: `sudo apt install python3-tk`).

```bash
git clone <URL-DEL-REPOSITORIO>
cd sistema-experto-informatica
python main.py --help
```

## Ejecución

**Interfaz gráfica** (sin argumentos):

```bash
python main.py
```

1. La base de conocimiento por defecto se carga sola; use *Cargar base de conocimiento…* para otra.
2. Marque los síntomas en la lista **o** use *Cargar hechos desde archivo…* (por ejemplo `casos/caso_04_disco_fallando.txt`).
3. Elija la estrategia de conflictos y presione *Siguiente paso* para ver cada ciclo (conjunto de conflictos, regla elegida,
   motivo, hechos nuevos), o *Ejecutar todo*.
4. La recomendación aparece en el panel inferior al terminar.

**Consola:**

```bash
python main.py --hechos casos/caso_04_disco_fallando.txt               # desde archivo
python main.py --hechos casos/caso_02_lento_malware_y_ram.txt --paso-a-paso
python main.py --interactivo                                            # pregunta síntoma por síntoma
python main.py --hechos casos/caso_01_no_enciende.txt --criterios especificidad,orden   # estrategia original
python main.py --kb otra_base.json --hechos mis_hechos.json
```

**Pruebas:**

```bash
python -m unittest discover -s tests -v
```

## Formato de la base de conocimiento (`.json`)

```json
{
  "metadatos": {"nombre": "...", "dominio": "...", "version": "1.0"},
  "hechos": {
    "equipo_lento":   {"tipo": "sintoma",       "texto": "El equipo está muy lento"},
    "falla_ram":      {"tipo": "diagnostico",   "texto": "Falla en la memoria RAM"},
    "rec_ampliar_ram":{"tipo": "recomendacion", "texto": "Ampliar la memoria RAM..."}
  },
  "reglas": [
    {"id": "R21", "nombre": "Memoria RAM insuficiente",
     "si": ["equipo_lento", "uso_ram_alto"], "entonces": ["memoria_insuficiente"],
     "prioridad": 5, "explicacion": "Lentitud con RAM casi llena..."}
  ]
}
```

* **Regla** = `SI antecedentes (conjunción) ENTONCES consecuentes`. Campos obligatorios: `id`, `nombre`, `si`, `entonces`.
  Opcionales: `prioridad` (por defecto 5; mayor = más urgente) y `explicacion`.
* **Catálogo de hechos** (`hechos`): `tipo` ∈ `sintoma` (se pregunta al usuario), `diagnostico`, `recomendacion`
  (salida del sistema) e `intermedio` (por defecto para hechos no catalogados). Los síntomas alimentan la lista de la GUI
  y las preguntas de la consola.
* Al cargar, se valida: ids únicos, reglas completas, tipos válidos y avisos de hechos inalcanzables o síntomas sin usar.

## Formato de los hechos iniciales (Memoria de Trabajo)

* `.txt`: un hecho por línea; `#` inicia un comentario.
* `.json`: lista `["tos", "fiebre"]` o diccionario `{"tos": true, "fiebre": false}` (también dentro de la clave `"hechos"`).
  **Solo los valores verdaderos entran a la memoria.**

> Mejora respecto al código original: allí `set(datos.keys())` convertía en hecho cualquier clave, incluso con valor `False`
> (por ejemplo `dolor_garganta: False`), lo que podía disparar reglas con síntomas ausentes.

## Estrategia de resolución de conflictos

El motor sigue el ciclo **emparejar → resolver conflicto → actuar** hasta que el conjunto de conflictos queda vacío.
Las reglas aplicables forman el *conjunto de conflictos*; para elegir una se aplican, **en cascada**, estos criterios
(cada uno desempata al anterior):

| # | Criterio | Descripción | Referente |
|---|----------|-------------|-----------|
| 0 | **Refracción** | Una regla ya disparada no vuelve a dispararse (evita ciclos infinitos). Siempre activa. | OPS5, CLIPS; criterio *a)* del código original |
| 1 | **Prioridad** (*salience*) | Mayor `prioridad` declarada en la regla (p. ej. proteger datos o contener malware antes que otras acciones). | CLIPS (`declare (salience n)`) |
| 2 | **Especificidad** | Gana la regla con más antecedentes (más específica). | OPS5, CLIPS (*complexity*); criterio *b)* del código original |
| 3 | **Recencia** | Gana la regla que usa hechos agregados más recientemente: se comparan, de mayor a menor, los ciclos de sus antecedentes (los datos iniciales valen 0). Favorece profundizar la línea de razonamiento actual. | OPS5 estrategia LEX, CLIPS (*depth*); criterio *c)* del código original |
| 4 | **Orden** | Primera regla en el archivo de conocimiento (desempate determinista). Alternativa: `azar` con semilla reproducible. | CLIPS (*random*); criterio *d)* del código original |

El orden de los criterios es configurable (GUI: lista de estrategias; CLI: `--criterios`). Hay cuatro estrategias
predefinidas, incluida la **original del taller** (`especificidad > orden`) para comparar resultados.
Cada ciclo muestra el valor de cada criterio para cada candidata y explica **por qué** ganó la regla elegida.

**Elementos agregados al código original:** prioridad explícita (*salience*), recencia efectiva con marcas de ciclo en la
memoria de trabajo, orden determinista/azar con semilla y trazabilidad de la decisión.

### Referentes

* Forgy, C. L. (1981). *OPS5 User's Manual* (CMU-CS-81-135). Carnegie Mellon University. — estrategias LEX y MEA.
* McDermott, J. y Forgy, C. (1978). «Production system conflict resolution strategies». En Waterman y Hayes-Roth (eds.),
  *Pattern-Directed Inference Systems*. Academic Press.
* Brownston, L., Farrell, R., Kant, E. y Martin, N. (1985). *Programming Expert Systems in OPS5*. Addison-Wesley.
* Giarratano, J. y Riley, G. (2005). *Expert Systems: Principles and Programming* (4.ª ed.). Thomson. — CLIPS: salience,
  depth, breadth, simplicity, complexity, LEX, MEA, random.
* *CLIPS Basic Programming Guide* — sección de estrategias de resolución de conflictos y *salience*.
* Russell, S. y Norvig, P. *Artificial Intelligence: A Modern Approach* — encadenamiento hacia adelante y sistemas de producción.
* Luger, G. *Artificial Intelligence: Structures and Strategies for Complex Problem Solving* — sistemas de producción
  (refracción, recencia, especificidad).

## Caso de estudio: soporte técnico informático

* 36 síntomas, 13 diagnósticos, 16 recomendaciones y 39 reglas (`conocimiento/base_conocimiento_informatica.json`).
* Encadenamiento ejemplo (caso 4): `equipo_lento + disco_uso_100 → cuello_botella_disco` (R17) →
  `+ ruidos_clic_disco → falla_disco_fisico` (R18) → `rec_respaldar_y_reemplazar_disco` (R19).

| Caso | Archivo | Resultado esperado |
|------|---------|--------------------|
| 1 | `casos/caso_01_no_enciende.txt` | Falla de fuente de poder → reemplazarla |
| 2 | `casos/caso_02_lento_malware_y_ram.txt` | Malware (urgente) y RAM insuficiente; conflictos entre varias reglas |
| 3 | `casos/caso_03_sin_internet_dns.txt` | Falla de DNS → configurar DNS alternativos |
| 4 | `casos/caso_04_disco_fallando.txt` | Falla física de disco (respaldar y reemplazar) y migrar a SSD |
| 5 | `casos/caso_05_sobrecalentamiento.txt` | Sobrecalentamiento → limpieza física y revisión de disipación |
| 6 | `casos/caso_06_datos_insuficientes.txt` | Sin recomendación (faltan datos) |
| 7 | `casos/caso_07_arranque.json` | Arranque corrupto → reparar arranque (formato JSON, ignora `false`) |

## Estructura de carpetas

```
sistema-experto-informatica/
├── main.py                       # punto de entrada (GUI sin argumentos, CLI con argumentos)
├── README.md
├── requirements.txt              # sin dependencias externas
├── conocimiento/
│   └── base_conocimiento_informatica.json   # base de conocimiento (39 reglas)
├── casos/                        # hechos iniciales de ejemplo (.txt y .json)
├── sistema_experto/
│   ├── base_conocimiento.py      # clases Regla y BaseConocimiento (carga y validación)
│   ├── hechos.py                 # carga de hechos desde archivo o por interacción
│   ├── motor.py                  # motor de inferencia, sesión paso a paso y estrategia de conflictos
│   ├── reporte.py                # formateo de la traza y la conclusión
│   ├── cli.py                    # interfaz de consola
│   └── gui.py                    # interfaz gráfica (Tkinter)
└── tests/
    └── test_sistema.py           # pruebas automáticas (unittest)
```

## Cómo ampliar la base

Agregue reglas al JSON (ids únicos) y, si introduce síntomas nuevos, regístrelos en `hechos` con `"tipo": "sintoma"`.
Al cargar el archivo, el sistema avisa de hechos inalcanzables o síntomas sin usar. No hace falta modificar el código.
