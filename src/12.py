import pygame
import sys
import os
import random

# --- 1. CONFIGURACIÓN ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
pygame.mixer.init()

# --- CARGA Y REPRODUCCIÓN DE MÚSICA ---
ruta_musica = os.path.join(base_path, "monkey.mp3")
if os.path.exists(ruta_musica):
    try:
        pygame.mixer.music.load(ruta_musica)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"No se pudo reproducir la música: {e}")

info = pygame.display.Info()
ANCHO, ALTO = info.current_w, info.current_h
ALTURA_PASTO = 220 
META_X = 10000 
TAMANO_JUGADOR = (200, 170)

pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWSURFACE)
fuente_menu = pygame.font.SysFont("Arial", 80, bold=True)
fuente_hud = pygame.font.SysFont("Arial", 40, bold=True)

# --- 2. ASSETS ---
def cargar_asset(nombre, tamaño_fijo=None):
    ruta = os.path.join(base_path, nombre)
    if not os.path.exists(ruta): return None
    try:
        img = pygame.image.load(ruta).convert_alpha()
        if tamaño_fijo: img = pygame.transform.scale(img, tamaño_fijo)
        return img
    except: return None

def obtener_skins(nombre, tamaño):
    base = cargar_asset(nombre, tamaño)
    if base:
        return (base, pygame.transform.flip(base, True, False))
    s = pygame.Surface(tamaño); s.fill((255, 0, 255)) 
    return (s, s)

# Skins
p1_normal = obtener_skins("imagen.png", TAMANO_JUGADOR)
p1_canicas = obtener_skins("imagen_poder.png", TAMANO_JUGADOR)
p1_velocidad = obtener_skins("imagen5.png", TAMANO_JUGADOR)
p2_normal = obtener_skins("original.png", TAMANO_JUGADOR)
p2_canicas = obtener_skins("original1.png", TAMANO_JUGADOR)
p2_velocidad = obtener_skins("original1_poder.png", TAMANO_JUGADOR)

img_fondo = cargar_asset("fondo1.png", (ANCHO, ALTO))
img_bloque_q = cargar_asset("bloque2.png", (100, 100))
img_bloque_v = cargar_asset("bloque3.png", (100, 100))
img_postobon = cargar_asset("enemigo1.png", (60, 100))
img_variante1 = cargar_asset("variante1.png", (60, 60))
img_variante2 = cargar_asset("variante2.png", (60, 60))

# --- 3. CLASES ---
class SistemaCamara:
    def __init__(self): self.scroll = 0
    def aplicar(self, rect): return rect.move(-int(self.scroll), 0)
    def actualizar(self, jugadores):
        if not jugadores: return
        px = sum(p.rect.x for p in jugadores) // len(jugadores)
        self.scroll += (px - self.scroll - ANCHO//3) / 10

class Canica:
    def __init__(self, x, y, direccion):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.vx = 35 if direccion == "DER" else -35

    def actualizar(self, bloques, enemigos):
        self.rect.x += self.vx
        
        # Colisión con bloques (los destruye)
        for b in bloques[:]:
            if self.rect.colliderect(b.rect):
                bloques.remove(b) # Aquí se elimina el bloque
                return True # Elimina la canica
        
        # Colisión con enemigos
        for e in enemigos[:]:
            if self.rect.colliderect(e.rect): 
                enemigos.remove(e)
                return True # Elimina la canica
                
        return self.rect.x < 0 or self.rect.x > META_X + 2000

class Jugador:
    def __init__(self, x, y, controles, tipo):
        self.rect = pygame.Rect(x, y, TAMANO_JUGADOR[0], TAMANO_JUGADOR[1])
        self.controles = controles
        self.tipo = tipo 
        self.vel_y, self.dir = 0, "DER"
        self.tiene_canicas = False
        self.super_velocidad = False
        self.timer_poder = 0
        self.cooldown = 0
    
    def actualizar(self, bloques, enemigos, items, canicas, teclas):
        if self.cooldown > 0: self.cooldown -= 1
        if self.timer_poder > 0: 
            self.timer_poder -= 1
            if self.timer_poder <= 0: self.super_velocidad = False
        
        v_base = 22 if self.super_velocidad else 12
        if teclas[self.controles['izq']]:
            self.rect.x -= v_base
            self.dir = "IZQ"
        if teclas[self.controles['der']]:
            self.rect.x += v_base
            self.dir = "DER"
        
        self.vel_y += 2.2
        self.rect.y += self.vel_y
        en_suelo = False

        if self.rect.bottom >= ALTO-ALTURA_PASTO:
            self.rect.bottom = ALTO-ALTURA_PASTO
            self.vel_y, en_suelo = 0, True

        for b in bloques:
            if self.rect.colliderect(b.rect):
                if self.vel_y > 0 and self.rect.bottom < b.rect.centery + 20:
                    self.rect.bottom = b.rect.top; self.vel_y, en_suelo = 0, True
                elif self.vel_y < 0:
                    self.rect.top = b.rect.bottom; self.vel_y = 2
                    if b.es_especial and not b.golpeado:
                        b.golpeado = True
                        tp = 'p1' if random.random() < 0.5 else 'p2'
                        img = img_variante1 if tp == 'p1' else img_variante2
                        items.append(Item(b.rect.x+20, b.rect.y-80, img, tp))
        
        if teclas[self.controles['salto']] and en_suelo:
            self.vel_y = -40
        
        if teclas[self.controles['disparo']] and self.tiene_canicas and self.cooldown == 0:
            canicas.append(Canica(self.rect.centerx, self.rect.centery, self.dir))
            self.cooldown = 15

        for it in items[:]:
            if self.rect.colliderect(it.rect):
                if it.tipo == 'p1': self.tiene_canicas = True
                else: self.super_velocidad = True; self.timer_poder = 600
                items.remove(it)

        for e in enemigos[:]:
            if self.rect.colliderect(e.rect):
                if self.super_velocidad or (self.vel_y > 0 and self.rect.bottom < e.rect.centery + 20):
                    enemigos.remove(e); self.vel_y = -20
                else: return "MUERTE"
        return "MUERTE" if self.rect.y > ALTO else None

    def dibujar(self, superficie, camara):
        if self.tipo == 1:
            skins = p1_velocidad if self.super_velocidad else (p1_canicas if self.tiene_canicas else p1_normal)
        else:
            skins = p2_velocidad if self.super_velocidad else (p2_canicas if self.tiene_canicas else p2_normal)
        img = skins[0] if self.dir == "DER" else skins[1]
        superficie.blit(img, camara.aplicar(self.rect))

class Bloque:
    def __init__(self, x, y, img, es_especial=False):
        self.rect = pygame.Rect(x, y, 100, 100); self.img = img; self.es_especial = es_especial; self.golpeado = False

class Item:
    def __init__(self, x, y, img, tipo):
        self.rect = pygame.Rect(x, y, 60, 60); self.img = img; self.tipo = tipo; self.vy = -15
    def actualizar(self):
        self.vy += 1.2; self.rect.y += self.vy
        if self.rect.bottom >= ALTO-ALTURA_PASTO: self.rect.bottom = ALTO-ALTURA_PASTO; self.vy = 0

class Enemigo:
    def __init__(self, x, y, img):
        self.rect = pygame.Rect(x, y, 60, 100); self.img = img; self.vx = -6
    def actualizar(self): self.rect.x += self.vx

# --- 4. FLUJO ---
VIDAS = 3

def menu():
    while True:
        pantalla.fill((50, 150, 250))
        if img_fondo: pantalla.blit(img_fondo, (0,0))
        t = fuente_menu.render("THE AMIRDOWS GAME", True, (255,255,255))
        o1 = fuente_hud.render("1: SOLO | 2: MULTI | S: SALIR", True, (255,255,0))
        pantalla.blit(t, (ANCHO//2-t.get_width()//2, 150))
        pantalla.blit(o1, (ANCHO//2-o1.get_width()//2, 400))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: return 1
                if e.key == pygame.K_2: return 2
                if e.key == pygame.K_s: pygame.quit(); sys.exit()

def partida(n_jug, nivel):
    global VIDAS
    cam, reloj = SistemaCamara(), pygame.time.Clock()
    c1 = {'izq': pygame.K_LEFT, 'der': pygame.K_RIGHT, 'salto': pygame.K_UP, 'disparo': pygame.K_l}
    c2 = {'izq': pygame.K_a, 'der': pygame.K_d, 'salto': pygame.K_w, 'disparo': pygame.K_g}
    jugs = [Jugador(100, ALTO-400, c1, 1)]
    if n_jug == 2: jugs.append(Jugador(250, ALTO-400, c2, 2))
    
    bloques = [Bloque(i*450, random.randint(400, 600), img_bloque_q, True) for i in range(1, 25)]
    enemigos = [Enemigo(random.randint(1000, META_X), ALTO-ALTURA_PASTO-100, img_postobon) for _ in range(10 + nivel*5)]
    items, canicas = [], []

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        
        teclas = pygame.key.get_pressed()
        for p in jugs:
            estado = p.actualizar(bloques, enemigos, items, canicas, teclas)
            if estado == "MUERTE":
                VIDAS -= 1
                return "FIN" if VIDAS <= 0 else "REINTENTAR"
            if p.rect.x > META_X: return "SIGUIENTE"

        cam.actualizar(jugs)
        for e in enemigos: e.actualizar()
        for it in items: it.actualizar()
        
        # Lógica de actualización de canicas pasando las listas de bloques y enemigos
        for c in canicas[:]:
            if c.actualizar(bloques, enemigos): canicas.remove(c)

        pantalla.fill((107, 140, 255))
        if img_fondo: pantalla.blit(img_fondo, (-(int(cam.scroll*0.3)%ANCHO), 0))
        pygame.draw.rect(pantalla, (34, 139, 34), (0, ALTO-ALTURA_PASTO, ANCHO, ALTURA_PASTO))
        
        for b in bloques: 
            pantalla.blit(img_bloque_v if b.golpeado else b.img, cam.aplicar(b.rect))
        for it in items: pantalla.blit(it.img, cam.aplicar(it.rect))
        for e in enemigos: pantalla.blit(e.img, cam.aplicar(e.rect))
        for p in jugs: p.dibujar(pantalla, cam)
        for c in canicas: pygame.draw.circle(pantalla, (255,255,255), cam.aplicar(c.rect).center, 12)
        
        pantalla.blit(fuente_hud.render(f"NIVEL: {nivel}  VIDAS: {VIDAS}", True, (255,255,255)), (50, 50))
        pygame.display.flip()
        reloj.tick(60)

if __name__ == "__main__":
    while True:
        modo = menu(); nivel, VIDAS = 1, 3
        while nivel <= 5:
            res = partida(modo, nivel)
            if res == "SIGUIENTE": nivel += 1
            elif res == "FIN": break