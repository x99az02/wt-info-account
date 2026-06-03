import re
import requests
from bs4 import BeautifulSoup
import flet as ft

def consultar_conta_wartale(usuario, senha):
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8',
        'Connection': 'keep-alive'
    }
    try:
        url_inicial = 'https://user.wartale.com/index.asp?page=2'
        response_init = session.get(url_inicial, headers=headers, timeout=15)
        soup_init = BeautifulSoup(response_init.text, 'html.parser')
        form = soup_init.find('form', {'id': 'loginaccount'})
        
        if not form or not form.get('action'):
            return {"erro": "Não foi possível localizar o formulário de login no site."}
            
        action_url = form.get('action')
        LOGIN_URL = f"https://user.wartale.com{action_url}" if action_url.startswith('/') else f"https://user.wartale.com/{action_url}"
        
        payload = {'acc': usuario, 'pw': senha}
        response_login = session.post(LOGIN_URL, data=payload, headers=headers, timeout=15)
        
        if "Account does not exist or Password is incorrect" in response_login.text:
            return {"erro": "Conta não existe ou senha incorreta!"}

        ACCOUNT_URL = 'https://user.wartale.com/index.asp?page=2&action=0'
        panel_response = session.get(ACCOUNT_URL, headers=headers, timeout=15)
        html_content = panel_response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if soup.find('input', {'name': 'acc'}) and soup.find('input', {'name': 'pw'}):
            return {"erro": "O site recusou as credenciais enviadas."}

        info = {'Coins': '0', 'GlobalStatus': 'Offline In-Game', 'OnlineChar': None, 'Chars': []}
        
        match_online = re.search(r'In-game<\/b><\/span>\s+on\s+(.+?)\s+at\s+[A-Za-z0-9]+', html_content, re.IGNORECASE | re.DOTALL)
        if match_online:
            char_name = match_online.group(1).strip()
            info['GlobalStatus'] = f'Online no personagem {char_name}'
            info['OnlineChar'] = char_name

        coin_div = soup.find('div', title="Visit a Coin Shop NPC in-game")
        if coin_div and coin_div.find('strong'):
            info['Coins'] = coin_div.find('strong').text.strip()

        char_table = None
        for table in soup.find_all('table'):
            if table.find(string=lambda text: text and "Name" in text):
                if len(table.find_all('tr')) > 1:
                    char_table = table
                    break
                
        if char_table:
            rows = char_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    char_name = cells[2].text.strip()
                    if not char_name or char_name.lower() in ["name", "character"]:
                        continue
                    
                    class_title = cells[4].get('title', '').strip()
                    if not class_title:
                        class_title = cells[4].text.strip()
                        
                    level = cells[5].text.strip()
                    exp = cells[6].text.strip()
                    
                    status = 'OFFLINE'
                    if info['OnlineChar'] and char_name.lower() == info['OnlineChar'].lower():
                        status = 'ONLINE'

                    info['Chars'].append({
                        'Name': char_name, 'Class': class_title if class_title else 'Desconhecida',
                        'Level': level, 'Exp': exp, 'Status': status
                    })
        return info
    except Exception as e:
        return {"erro": f"Erro de conexão: {str(e)}"}


def main(page: ft.Page):
    page.title = "Wartale Mobile Consultor"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    
    page.window_width = 390
    page.window_height = 740

    txt_user = ft.TextField(label="Usuário (Account)", prefix_icon=ft.Icons.PERSON, border_color="amber400")
    txt_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, border_color="amber400")
    lbl_erro = ft.Text(value="", color="red400", weight=ft.FontWeight.BOLD)
    loading = ft.ProgressRing(visible=False, color="amber400")

    def btn_conectar_click(e):
        if not txt_user.value or not txt_pass.value:
            lbl_erro.value = "Preencha todos os campos!"
            page.update()
            return
            
        lbl_erro.value = ""
        loading.visible = True
        btn_conectar.disabled = True
        page.update()

        dados = consultar_conta_wartale(txt_user.value.strip(), txt_pass.value.strip())

        loading.visible = False
        btn_conectar.disabled = False

        if "erro" in dados:
            lbl_erro.value = dados["erro"]
            page.update()
        else:
            # Proteção para capturar erros de UI sem travar o app de vez
            try:
                exibir_painel(dados)
            except Exception as ex:
                lbl_erro.value = f"Erro ao renderizar painel: {str(ex)}"
                page.update()

    btn_conectar = ft.FilledButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.LOGIN, color="black"), ft.Text("Conectar Conta", color="black", weight=ft.FontWeight.BOLD)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        ),
        bgcolor="amber400",
        height=50,
        on_click=btn_conectar_click
    )

    view_login = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
        controls=[
            ft.Container(height=40),
            ft.Icon(ft.Icons.SHIELD_MOON, size=80, color="amber400"),
            ft.Text("WARTALE MANAGER", size=24, weight=ft.FontWeight.BOLD, color="amber400"),
            ft.Text("Consulte seus personagens em tempo real", size=14, color="grey400"),
            ft.Container(height=10),
            txt_user,
            txt_pass,
            lbl_erro,
            loading,
            btn_conectar
        ]
    )

    def exibir_painel(dados):
        page.clean()
        
        def voltar(e):
            page.clean()
            page.add(view_login)
            page.update()

        btn_voltar = ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="amber400", on_click=voltar)
        
        card_resumo = ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.MONEY, color="amber400"),
                        ft.Text(f"Wartale Coins: {dados['Coins']}", size=18, weight=ft.FontWeight.BOLD)
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(color="grey700"),
                    ft.Row([
                        ft.Icon(ft.Icons.WIFI, color="green400" if "Online" in dados['GlobalStatus'] else "grey500"),
                        ft.Text(dados['GlobalStatus'], size=13, color="grey300")
                    ])
                ])
            ),
            bgcolor="surfaceVariant"
        )

        lista_personagens = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        for char in dados['Chars']:
            is_online = char['Status'] == 'ONLINE'
            
            # CORREÇÃO: O 'border' saiu do ft.Card e foi para dentro do ft.Container
            card_char = ft.Card(
                content=ft.Container(
                    padding=15,
                    border=ft.Border.all(1, "amber400") if is_online else None,
                    border_radius=8, # adicionado para manter o design bonito com a borda
                    content=ft.Row([
                        ft.Column([
                            ft.Text(char['Name'], size=18, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Text(f"Classe: {char['Class']}", size=13, color="grey400"),
                            ft.Text(f"XP: {char['Exp']}", size=11, color="grey500"),
                        ], spacing=3, expand=True),
                        
                        ft.Column([
                            ft.Container(
                                content=ft.Text(f"LV {char['Level']}", weight=ft.FontWeight.BOLD, color="black"),
                                bgcolor="amber400",
                                padding=6,
                                border_radius=6
                            ),
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor="green" if is_online else "red", shape=ft.BoxShape.CIRCLE),
                                ft.Text(char['Status'], size=11, weight=ft.FontWeight.BOLD, color="green" if is_online else "red300")
                            ], spacing=5)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ])
                )
            )
            lista_personagens.controls.append(card_char)

        page.add(
            ft.Row([btn_voltar, ft.Text("Seu Painel Wartale", size=18, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.START),
            card_resumo,
            ft.Container(height=10),
            ft.Text("Meus Personagens:", size=16, weight=ft.FontWeight.BOLD, color="amber400"),
            lista_personagens
        )
        page.update()

    page.add(view_login)

ft.run(main, view=ft.AppView.WEB_BROWSER)