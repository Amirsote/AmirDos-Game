import pygame
import sys
import os
import random
import socket
import threading

# --- 1. CONFIGURACIÓN ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
pygame.mixer.init()

# Variables de Red Globales
cliente_socket = None
conectado_online = False
es_servidor = False
# Datos remotos: [x, y, dir, tiene_canicas, super_velocidad]
pos_remota = [250, 100, "DER", False, False] 
nick_remoto = "Invitado"
mi_nickname = "Amir"
ip_servidor_input = "127.0.0.1"

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
    if base: return (base, pygame.transform.flip(base, True, False))
    s = pygame.Surface(tamaño); s.fill((255, 0, 255)) 
    return (s, s)

# Configuración Visual
info = pygame.display.Info()
ANCHO, ALTO = info.current_w, info.current_h
ALTURA_PASTO = 220 
META_X = 10000 
TAMANO_JUGADOR = (200, 170)

pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWSURFACE)
fuente_menu = pygame.font.SysFont("Arial", 80, bold=True)
fuente_hud = pygame.font.SysFont("Arial", 40, bold=True)
fuente_gui = pygame.font.SysFont("Arial", 32, bold=True)

# Assets (Usa tus nombres de archivo originales)
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

# --- 3. SISTEMA DE RED ---
def hilo_recibir():
    global pos_remota, nick_remoto, conectado_online
    while conectado_online:
        try:
            data = cliente_socket.recv(1024).decode()
            if data:
                p = data.split("|")
                if len(p) >= 6:
                    pos_remota[0], pos_remota[1] = int(float(p[0])), int(float(p[1]))
                    pos_remota[2] = p[2]
                    pos_remota[3] = p[3] == "True"
                    pos_remota[4] = p[4] == "True"
                    nick_remoto = p[5]
        except:
            conectado_online = False
            break

def servidor_esperar():
    global cliente_socket, conectado_online, es_servidor
    try:
        es_servidor = True
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 5555))
        s.listen(1)
        cliente_socket, _ = s.accept()
        conectado_online = True
        threading.Thread(target=hilo_recibir, daemon=True).start()
    except:
        es_servidor = False

def cliente_conectar(ip):
    global cliente_socket, conectado_online, es_servidor
    try:
        es_servidor = False
        cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente_socket.settimeout(5)
        cliente_socket.connect((ip, 5555))
        conectado_online = True
        threading.Thread(target=hilo_recibir, daemon=True).start()
    except:
        conectado_online = False

# --- 4. CLASES ---
class SistemaCamara:
    def __init__(self): self.scroll = 0
    def aplicar(self, rect): return rect.move(-int(self.scroll), 0)
    def actualizar(self, p):
        self.scroll += (p.rect.x - self.scroll - ANCHO//3) / 10

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
        
        v = 22 if self.super_velocidad else 12
        dx = 0
        if teclas[self.controles['izq']]: dx = -v; self.dir = "IZQ"
        if teclas[self.controles['der']]: dx = v; self.dir = "DER"
        self.rect.x += dx
        
        self.vel_y += 2.2
        self.rect.y += self.vel_y
        en_suelo = False
        if self.rect.bottom >= ALTO-ALTURA_PASTO:
            self.rect.bottom = ALTO-ALTURA_PASTO; self.vel_y, en_suelo = 0, True

        for b in bloques:
            if self.rect.colliderect(b.rect):
                if self.vel_y > 0 and self.rect.bottom < b.rect.centery + 20:
                    self.rect.bottom = b.rect.top; self.vel_y, en_suelo = 0, True
                elif self.vel_y < 0:
                    self.rect.top = b.rect.bottom; self.vel_y = 2
                    if b.es_especial and not b.golpeado:
                        b.golpeado = True
                        items.append(Item(b.rect.x+20, b.rect.y-80, 'poder1' if random.random()<0.5 else 'poder2'))
        
        if teclas[self.controles['salto']] and en_suelo: self.vel_y = -46 if self.super_velocidad else -40
        return "MUERTE" if self.rect.y > ALTO else None

    def dibujar(self, superficie, camara, nick, rem_data=None):
        if rem_data:
            x, y, d, can, vel = rem_data
            r = camara.aplicar(pygame.Rect(x, y, TAMANO_JUGADOR[0], TAMANO_JUGADOR[1]))
            s = p2_velocidad if vel else (p2_canicas if can else p2_normal)
            img = s[0] if d == "DER" else s[1]
        else:
            r = camara.aplicar(self.rect)
            s = p1_velocidad if self.super_velocidad else (p1_canicas if self.tiene_canicas else p1_normal)
            if self.tipo == 2: s = p2_velocidad if self.super_velocidad else (p2_canicas if self.tiene_canicas else p2_normal)
            img = s[0] if self.dir == "DER" else s[1]
        superficie.blit(img, r)
        superficie.blit(fuente_gui.render(nick, True, (255,255,255)), (r.x, r.y - 40))

class Bloque:
    def __init__(self, x, y, img, es_especial=False):
        self.rect = pygame.Rect(x, y, 100, 100); self.img = img; self.es_especial = es_especial; self.golpeado = False

class Item:
    def __init__(self, x, y, tipo):
        self.rect = pygame.Rect(x, y, 60, 60); self.tipo = tipo; self.vy = -15
        self.img = img_variante1 if tipo == 'poder1' else img_variante2
    def actualizar(self):
        self.vy += 1.2; self.rect.y += self.vy
        if self.rect.bottom >= ALTO-ALTURA_PASTO: self.rect.bottom = ALTO-ALTURA_PASTO; self.vy = 0

# --- 5. MENÚS ---
def pantalla_online():
    global mi_nickname, ip_servidor_input, conectado_online, es_servidor
    foco = "nick"
    esperando_red = False
    
    while not conectado_online:
        pantalla.fill((30, 40, 70))
        mx, my = pygame.mouse.get_pos()
        
        # Cajas de texto
        txt_n = fuente_gui.render(f"TU NICK: {mi_nickname}" + ("|" if foco=="nick" else ""), True, (255,255,255))
        txt_i = fuente_gui.render(f"IP DESTINO: {ip_servidor_input}" + ("|" if foco=="ip" else ""), True, (255,255,255))
        pantalla.blit(txt_n, (100, 200)); pantalla.blit(txt_i, (100, 300))
        
        # Botones
        btn_h = pygame.Rect(100, 450, 220, 70)
        btn_j = pygame.Rect(380, 450, 220, 70)
        
        col_h = (0, 255, 0) if btn_h.collidepoint(mx, my) else (0, 180, 0)
        col_j = (0, 100, 255) if btn_j.collidepoint(mx, my) else (0, 0, 200)
        
        pygame.draw.rect(pantalla, col_h, btn_h, border_radius=10)
        pygame.draw.rect(pantalla, col_j, btn_j, border_radius=10)
        
        pantalla.blit(fuente_gui.render("SER HOST", True, (0,0,0)), (135, 465))
        pantalla.blit(fuente_gui.render("UNIRSE", True, (255,255,255)), (430, 465))

        if esperando_red:
            msg = "ESPERANDO JUGADOR..." if es_servidor else "INTENTANDO CONECTAR..."
            pantalla.blit(fuente_hud.render(msg, True, (255,255,0)), (100, 550))

        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_TAB: foco = "ip" if foco=="nick" else "nick"
                elif e.key == pygame.K_BACKSPACE:
                    if foco=="nick": mi_nickname = mi_nickname[:-1]
                    else: ip_servidor_input = ip_servidor_input[:-1]
                else:
                    if foco=="nick" and len(mi_nickname)<12: mi_nickname += e.unicode
                    elif foco=="ip" and len(ip_servidor_input)<15: ip_servidor_input += e.unicode
            
            if e.type == pygame.MOUSEBUTTONDOWN:
                if btn_h.collidepoint(e.pos) and not esperando_red:
                    esperando_red = True; es_servidor = True
                    threading.Thread(target=servidor_esperar, daemon=True).start()
                if btn_j.collidepoint(e.pos) and not esperando_red:
                    esperando_red = True; es_servidor = False
                    threading.Thread(target=cliente_conectar, args=(ip_servidor_input,), daemon=True).start()
        
        pygame.display.flip()

def menu_principal():
    while True:
        pantalla.fill((0,0,0))
        if img_fondo: pantalla.blit(img_fondo, (0,0))
        t = fuente_menu.render("AMIRDOWS GAME", True, (255,255,255))
        pantalla.blit(t, (ANCHO//2 - t.get_width()//2, 100))
        
        opciones = [("1. SOLO", 300, "solo"), ("2. LOCAL", 420, "local"), ("3. ONLINE", 540, "online")]
        for texto, y, modo in opciones:
            txt = fuente_hud.render(texto, True, (255,255,0))
            rect = txt.get_rect(center=(ANCHO//2, y))
            pantalla.blit(txt, rect)
            if pygame.mouse.get_pressed()[0] and rect.collidepoint(pygame.mouse.get_pos()):
                return modo
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        pygame.display.flip()

# --- 6. PARTIDA ---
def partida(modo, nivel):
    global VIDAS, conectado_online
    if modo == "online": pantalla_online()
    
    cam, reloj = SistemaCamara(), pygame.time.Clock()
    c1 = {'izq': pygame.K_LEFT, 'der': pygame.K_RIGHT, 'salto': pygame.K_UP, 'disparo': pygame.K_l}
    c2 = {'izq': pygame.K_a, 'der': pygame.K_d, 'salto': pygame.K_w, 'disparo': pygame.K_g}
    
    jugs = [Jugador(100, ALTO-400, c1, 1)]
    if modo == "local": jugs.append(Jugador(250, ALTO-400, c2, 2))
    
    bloques = [Bloque(i*450, random.randint(400, 600), img_bloque_q, True) for i in range(1, 25)]
    items = []

    while True:
        reloj.tick(60); teclas = pygame.key.get_pressed()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()

        if conectado_online:
            try:
                p = jugs[0]
                msg = f"{p.rect.x}|{p.rect.y}|{p.dir}|{p.tiene_canicas}|{p.super_velocidad}|{mi_nickname}"
                cliente_socket.send(msg.encode())
            except: conectado_online = False

        for p in jugs:
            if p.actualizar(bloques, [], items, [], teclas) == "MUERTE": return "FIN"
            if p.rect.x > META_X: return "SIGUIENTE"

        cam.actualizar(jugs[0])
        for it in items: it.actualizar()

        pantalla.fill((107, 140, 255))
        pygame.draw.rect(pantalla, (34, 139, 34), (0, ALTO-ALTURA_PASTO, ANCHO, ALTURA_PASTO))
        for b in bloques: pantalla.blit(img_bloque_v if b.golpeado else b.img, cam.aplicar(b.rect))
        for it in items: pantalla.blit(it.img, cam.aplicar(it.rect))
        
        jugs[0].dibujar(pantalla, cam, mi_nickname if modo=="online" else "J1")
        if modo == "local": jugs[1].dibujar(pantalla, cam, "J2")
        if conectado_online: jugs[0].dibujar(pantalla, cam, nick_remoto, pos_remota)
        
        pygame.display.flip()

if __name__ == "__main__":
    while True:
        m = menu_principal(); partida(m, 1)