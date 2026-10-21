"""Interfaz gráfica (Tkinter, incluida en la biblioteca estándar de Python)."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import reporte
from .base_conocimiento import RUTA_KB_DEFECTO, BaseConocimiento, ErrorBaseConocimiento
from .hechos import ErrorHechos, cargar_hechos, separar_desconocidos
from .motor import ESTRATEGIAS_PREDEFINIDAS, EstrategiaConflictos, MotorInferencia


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Experto - Diagnóstico de fallas informáticas")
        self.geometry("1180x740")
        self.minsize(920, 580)
        self.kb = None
        self.sesion = None
        self.vars: dict[str, tk.BooleanVar] = {}
        self.extra: list[str] = []   # hechos cargados que no son síntomas del catálogo
        self._construir()
        if RUTA_KB_DEFECTO.exists():
            self.cargar_kb(RUTA_KB_DEFECTO)

    # ------------------------------------------------------------ construcción
    def _construir(self):
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill="x")
        ttk.Button(barra, text="1. Cargar base de conocimiento…",
                   command=self.elegir_kb).pack(side="left")
        ttk.Button(barra, text="2. Cargar hechos desde archivo…",
                   command=self.elegir_hechos).pack(side="left", padx=6)
        ttk.Button(barra, text="Limpiar hechos",
                   command=self.limpiar_hechos).pack(side="left")
        self.lbl_kb = ttk.Label(barra, text="Sin base de conocimiento")
        self.lbl_kb.pack(side="left", padx=12)

        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=6, pady=4)
        izq = ttk.LabelFrame(cuerpo, text="Hechos iniciales (síntomas observados)", padding=4)
        der = ttk.Frame(cuerpo)
        cuerpo.add(izq, weight=1)
        cuerpo.add(der, weight=3)

        # Lista de síntomas con barra de desplazamiento
        canvas = tk.Canvas(izq, width=340, highlightthickness=0)
        sb = ttk.Scrollbar(izq, orient="vertical", command=canvas.yview)
        self.marco_checks = ttk.Frame(canvas)
        self.marco_checks.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.marco_checks, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def rueda(ev):
            canvas.yview_scroll(-1 if (ev.num == 4 or ev.delta > 0) else 1, "units")

        def activar(_):
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                canvas.bind_all(ev, rueda)

        def desactivar(_):
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                canvas.unbind_all(ev)

        canvas.bind("<Enter>", activar)
        canvas.bind("<Leave>", desactivar)

        # Panel derecho: controles, traza y recomendación
        ctrl = ttk.Frame(der)
        ctrl.pack(fill="x")
        ttk.Label(ctrl, text="Estrategia de conflictos:").pack(side="left")
        self.combo = ttk.Combobox(ctrl, state="readonly", width=52,
                                  values=list(ESTRATEGIAS_PREDEFINIDAS))
        self.combo.current(0)
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.reiniciar())

        botones = ttk.Frame(der)
        botones.pack(fill="x", pady=6)
        ttk.Button(botones, text="Siguiente paso ▶", command=self.paso).pack(side="left")
        ttk.Button(botones, text="Ejecutar todo ⏩",
                   command=self.ejecutar_todo).pack(side="left", padx=6)
        ttk.Button(botones, text="Reiniciar", command=self.reiniciar).pack(side="left")

        marco_traza = ttk.LabelFrame(der, text="Inferencia paso a paso", padding=4)
        marco_traza.pack(fill="both", expand=True)
        self.txt_traza = scrolledtext.ScrolledText(
            marco_traza, height=18, state="disabled", font=("Courier New", 10), wrap="word")
        self.txt_traza.pack(fill="both", expand=True)

        marco_rec = ttk.LabelFrame(der, text="Recomendación del sistema experto", padding=4)
        marco_rec.pack(fill="both", expand=True, pady=(6, 0))
        self.txt_rec = scrolledtext.ScrolledText(
            marco_rec, height=11, state="disabled", font=("Courier New", 10), wrap="word")
        self.txt_rec.pack(fill="both", expand=True)

    # ----------------------------------------------------------------- carga
    def elegir_kb(self):
        ruta = filedialog.askopenfilename(
            title="Base de conocimiento", filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if ruta:
            self.cargar_kb(ruta)

    def cargar_kb(self, ruta):
        try:
            kb = BaseConocimiento.desde_archivo(ruta)
        except ErrorBaseConocimiento as e:
            messagebox.showerror("Base de conocimiento inválida", str(e))
            return
        self.kb = kb
        self.extra = []
        self._poblar_checks()
        self.reiniciar()
        nombre = kb.metadatos.get("nombre", "Base de conocimiento")
        self.lbl_kb.config(text=f"{nombre}: {len(kb.reglas)} reglas")
        if kb.advertencias:
            messagebox.showwarning("Avisos de la base de conocimiento",
                                   "\n".join(kb.advertencias))

    def _poblar_checks(self):
        for w in self.marco_checks.winfo_children():
            w.destroy()
        self.vars = {}
        for s in self.kb.sintomas():
            v = tk.BooleanVar(value=False)
            self.vars[s] = v
            tk.Checkbutton(self.marco_checks, text=self.kb.texto(s), variable=v,
                           anchor="w", justify="left", wraplength=300,
                           command=self.reiniciar).pack(anchor="w", pady=1)

    def elegir_hechos(self):
        if self.kb is None:
            messagebox.showwarning("Falta la base", "Primero cargue la base de conocimiento.")
            return
        ruta = filedialog.askopenfilename(
            title="Hechos iniciales",
            filetypes=[("Texto o JSON", "*.txt *.json"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            hechos = cargar_hechos(ruta)
        except ErrorHechos as e:
            messagebox.showerror("Archivo de hechos inválido", str(e))
            return
        validos, desconocidos = separar_desconocidos(self.kb, hechos)
        for v in self.vars.values():
            v.set(False)
        self.extra = [h for h in validos if h not in self.vars]
        for h in validos:
            if h in self.vars:
                self.vars[h].set(True)
        if desconocidos:
            messagebox.showwarning("Hechos ignorados",
                                   "No aparecen en la BC:\n" + ", ".join(desconocidos))
        self.reiniciar()

    def limpiar_hechos(self):
        for v in self.vars.values():
            v.set(False)
        self.extra = []
        self.reiniciar()

    # ------------------------------------------------------------- inferencia
    def hechos_seleccionados(self):
        return [h for h, v in self.vars.items() if v.get()] + self.extra

    def _asegurar_sesion(self) -> bool:
        if self.kb is None:
            messagebox.showwarning("Falta la base", "Cargue la base de conocimiento.")
            return False
        if self.sesion is None:
            hechos = self.hechos_seleccionados()
            if not hechos:
                messagebox.showinfo("Sin hechos",
                                    "Marque al menos un síntoma o cargue un archivo de hechos.")
                return False
            estrategia = EstrategiaConflictos(ESTRATEGIAS_PREDEFINIDAS[self.combo.get()])
            self.sesion = MotorInferencia(self.kb, estrategia).nueva_sesion(hechos)
            self._escribir(self.txt_traza,
                           reporte.formatear_memoria_inicial(self.kb, hechos) + "\n",
                           limpiar=True)
        return True

    def paso(self):
        if not self._asegurar_sesion():
            return
        if self.sesion.terminada:
            self._mostrar_conclusion()
            return
        p = self.sesion.siguiente_paso()
        if p is None:
            self._escribir(self.txt_traza, "\n" + "-" * 70 + "\n"
                           + reporte.formatear_sin_conflicto() + "\n")
            self._mostrar_conclusion()
        else:
            self._escribir(self.txt_traza, "\n" + reporte.formatear_paso(p, self.kb) + "\n")

    def ejecutar_todo(self):
        if not self._asegurar_sesion():
            return
        while not self.sesion.terminada:
            self.paso()
        self._mostrar_conclusion()

    def reiniciar(self):
        self.sesion = None
        self._escribir(self.txt_traza, "", limpiar=True)
        self._escribir(self.txt_rec, "", limpiar=True)

    def _mostrar_conclusion(self):
        self._escribir(self.txt_rec, reporte.formatear_conclusion(self.sesion), limpiar=True)

    @staticmethod
    def _escribir(widget, texto, limpiar=False):
        widget.config(state="normal")
        if limpiar:
            widget.delete("1.0", "end")
        widget.insert("end", texto)
        widget.see("end")
        widget.config(state="disabled")


def iniciar_gui():
    App().mainloop()
