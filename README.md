# Pinpoint PLN

**Autor:** Osmar Ciau

---

## Arquitectura y Funcionamiento Interno

El sistema implementa una arquitectura modular en tres capas desacopladas donde la interfaz de usuario no tiene dependencias de PLN, y los motores lingüísticos son servicios de Python puro independientes de la web:

```
[ Frontend (HTML5 + Vanilla JS) ]
               │
               ▼  JSON / REST API
[ API & Esquemas (FastAPI + Pydantic) ]
               │
               ▼  Llamadas de servicio
[ Orquestador del Juego (game_service.py) ]
       ├──> [ Cerebro Semántico (wordnet_service.py) ]  ──> WordNet / OMW 1.4
       └──> [ Motor Morfológico (nlp_service.py) ]      ──> FreeLing / NLTK
```

### Componentes Clave

1. **El Orquestador Central (`app/services/game_service.py`):**
   - Actúa como la máquina de estados del juego.
   - Gestiona las sesiones activas en memoria, administra el flujo de vidas e intentos, y calcula el puntaje dinámico (1000 a 200 pts según las pistas utilizadas).
   - Coordina la extracción de datos semánticos y delega la validación morfológica de cada intento.

2. **El Cerebro Semántico (`app/services/wordnet_service.py`):**
   - Consulta la ontología léxica de NLTK WordNet y Open Multilingual WordNet (`omw-1.4`).
   - Construye la jerarquía progresiva de 5 pistas (hiperónimo $\rightarrow$ co-hipónimo $\rightarrow$ hipónimos/merónimos $\rightarrow$ lema clave).
   - Filtra términos mediante frecuencia léxica empírica (corpus SemCor) para priorizar vocabulario cotidiano y garantiza que ninguna pista filtre la palabra solución.

3. **El Motor Morfológico (`app/services/nlp_service.py`):**
   - Normaliza las respuestas del usuario eliminando signos de puntuación, acentos diacríticos mediante descomposición canónica Unicode (NFD) y artículos determinantes/indeterminantes (*el*, *la*, *los*, *un*, *the*).
   - Lematiza con **FreeLing CLI** en español (con respaldo automático a `SnowballStemmer`) y **WordNetLemmatizer** en inglés.
   - Aplica una comparación en 3 etapas (coincidencia limpia $\rightarrow$ lematizada $\rightarrow$ raíz) para aceptar variaciones de género y número sin penalizaciones injustas.

4. **Controlador y Contratos de API (`app/api/game.py` y `app/schemas/game.py`):**
   - Expone los endpoints REST (`/api/game/new`, `/api/game/guess`, `/api/game/reveal`) y valida las entradas/salidas con esquemas Pydantic estrictos.

5. **Interfaz de Usuario (`app/templates/` y `app/static/`):**
   - Cliente interactivo estilo arcade retro de 8 bits desarrollado en Vanilla JS y Tailwind CSS, comunicado con el backend mediante peticiones asíncronas (`fetch`).

---

## Flujo de una Jugada

1. El usuario introduce una respuesta (por ejemplo, *"los martillos"*) y presiona Enter.
2. El cliente envía una petición `POST /api/game/guess` al controlador.
3. El controlador valida la solicitud con Pydantic y la entrega al **Orquestador** (`game_service.py`).
4. El orquestador solicita al **Motor Morfológico** (`nlp_service.py`) evaluar la entrada:
   - Se elimina el artículo *"los"*.
   - FreeLing extrae el lema canónico: `martillo`.
   - Se compara contra las formas canónicas precomputadas del concepto objetivo en memoria ($O(1)$).
5. El orquestador actualiza el estado de la partida (acierto, vidas, puntaje) y devuelve el resultado JSON para que el frontend actualice la pantalla y los efectos sonoros.

---

### 2. Iniciar el servidor
```bash
uv run python main.py
```
Disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 3. Ejecutar pruebas
```bash
uv run pytest
```
