import os
import io
import re
import sqlite3
import pandas as pd
import cv2
import numpy as np

from flask import Flask, request, jsonify, render_template, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image, ImageEnhance, ImageOps

from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image
import pytesseract
import os

# Forçar o caminho do Tesseract no servidor Render
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

app = Flask(__name__)

# Se estiver rodando localmente no Windows e precisar apontar o Tesseract, mude aqui:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
##TARIFAS REGRA DE NEGÓCIO (PAGAMENTO POR KM)
# ==================================

# ==================================
# TABELA DE TARIFAS E REGRA DE NEGÓCIO (PAGAMENTO POR KM)
# ==================================

def calcular_frete_por_veiculo(veiculo, km, pedagio, diaria):
    tarifas = {
        "fiorino": 2.20,
        "vlc": 2.80,
        "hr": 2.80,
        "3/4": 3.40,
        "toco": 4.10,
        "truck": 5.00,
        "carreta": 6.50
    }
    
    # Indentação corrigida: alinhada com o bloco da função
    veiculo_limpo = str(veiculo).strip().lower()
    
    # Procura a tarifa padrão. Se não encontrar o modelo exato, assume um valor médio de R$ 3.00/KM
    taxa_km = tarifas.get(veiculo_limpo, 3.00)
    
    # Executa o cálculo da regra de negócio
    return (km * taxa_km) + pedagio + diaria


# ==================================
# SQLITE CONFIGURAÇÃO (ESTRUTURA PLANILHA FRESCATTO)
# ==================================

def get_db():
    # Corrigido: adicionada a conexão ao banco que estava faltando
    conn = sqlite3.connect("/tmp/database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # TABELA UNIFICADA: Estrutura real da planilha de rotas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carga TEXT,
        data_carga TEXT,        -- Formato ISO: AAAA-MM-DD
        motorista TEXT,
        placa TEXT,
        veiculo TEXT,
        codigo_roteiro TEXT,    -- CÓD. ROT
        descricao_rota TEXT,    -- DESC. ROTA
        valor_coleta REAL,      -- VALOR COLET
        quantidade_entregas INTEGER, -- ENTREGAS
        peso REAL,
        volume REAL,
        valor_carga REAL,
        km REAL,
        pedagio REAL,
        diaria REAL,
        valor_frete REAL        -- VALOR FRETE (Faturamento calculado)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canhotos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nota_fiscal TEXT,
        cliente TEXT,
        carga TEXT,
        data_entrega TEXT,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devolucoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nota_fiscal TEXT,
        cliente TEXT,
        motivo TEXT,
        data TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


# Executa a inicialização do banco
init_db()
# ==================================


# ROTAS DE NAVEGAÇÃO (PÁGINAS)
# ==================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/canhotos")
def canhotos_page():
    return render_template("canhotos.html")

@app.route("/rotas")
def rotas_page():
   return render_template("rotas.html")

@app.route("/fretes")
def fretes_page():
   return render_template("fretes.html")

@app.route("/roteiros")
def roteiros_page():
   return render_template("roteiros.html")

@app.route("/devolucoes")
def devolucoes_page():
   return render_template("devolucoes.html")

@app.route("/relatorios")
def relatorios_page():
    conn = get_db()
    rotas = conn.execute("SELECT * FROM rotas").fetchall()
    canhotos = conn.execute("SELECT * FROM canhotos").fetchall()
    devolucoes = conn.execute("SELECT * FROM devolucoes").fetchall()
    conn.close()

    return render_template(
        "relatorios.html",
        data="Relatório geral",
        rotas=rotas,
        canhotos=canhotos,
        devolucoes=devolucoes
    )

# ==================================
# API: MÓDULO UNIFICADO DE ROTAS E FRETES (COM CÁLCULO DE KM)
# ==================================

# GET: Retorna as rotas
@app.route("/api/rotas", methods=["GET"])
@app.route("/api/roteiros", methods=["GET"])
@app.route("/api/fretes", methods=["GET"])
def get_rotas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM rotas").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# POST: Salva novas rotas executando o cálculo automático baseado no tipo de veículo por KM
@app.route("/api/rotas", methods=["POST"])
@app.route("/api/roteiros", methods=["POST"])
@app.route("/api/fretes", methods=["POST"])
def add_rota():
    dados = request.json
    conn = get_db()

    veiculo = dados.get("veiculo") or dados.get("tipo_veiculo") or "Padrão"
    km = float(dados.get("km") or 0)
    pedagio = float(dados.get("pedagio") or 0)
    diaria = float(dados.get("diaria") or 0)

    # Executa a regra da opção 2
    valor_final_frete = calcular_frete_por_veiculo(
        veiculo,
        km,
        pedagio,
        diaria
    )

    conn.execute("""
        INSERT INTO rotas (
            carga,
            data_carga,
            motorista,
            placa,
            veiculo,
            codigo_roteiro,
            descricao_rota,
            valor_coleta,
            quantidade_entregas,
            peso,
            volume,
            valor_carga,
            km,
            pedagio,
            diaria,
            valor_frete
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get("carga") or dados.get("rota"),
        dados.get("data_carga") or dados.get("data"),
        dados.get("motorista"),
        dados.get("placa"),
        veiculo,
        dados.get("codigo_roteiro") or dados.get("romaneio"),
        dados.get("descricao_rota"),
        dados.get("valor_coleta", 0),
        dados.get("quantidade_entregas", 0),
        dados.get("peso", 0),
        dados.get("volume", 0),
        dados.get("valor_carga", 0),
        km,
        pedagio,
        diaria,
        valor_final_frete
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "valor_calculado": valor_final_frete
    }), 201


# PUT: Atualiza as informações recalculando o valor do frete
@app.route("/api/rotas/<int:id>", methods=["PUT"])
@app.route("/api/roteiros/<int:id>", methods=["PUT"])
@app.route("/api/fretes/<int:id>", methods=["PUT"])
def update_rota(id):
    dados = request.json
    conn = get_db()

    veiculo = dados.get("veiculo") or dados.get("tipo_veiculo") or "Padrão"
    km = float(dados.get("km") or 0)
    pedagio = float(dados.get("pedagio") or 0)
    diaria = float(dados.get("diaria") or 0)

    valor_final_frete = calcular_frete_por_veiculo(
        veiculo,
        km,
        pedagio,
        diaria
    )

    conn.execute("""
        UPDATE rotas SET
            carga = ?,
            data_carga = ?,
            motorista = ?,
            placa = ?,
            veiculo = ?,
            codigo_roteiro = ?,
            descricao_rota = ?,
            valor_coleta = ?,
            quantidade_entregas = ?,
            peso = ?,
            volume = ?,
            valor_carga = ?,
            km = ?,
            pedagio = ?,
            diaria = ?,
            valor_frete = ?
        WHERE id = ?
    """, (
        dados.get("carga") or dados.get("rota"),
        dados.get("data_carga") or dados.get("data"),
        dados.get("motorista"),
        dados.get("placa"),
        veiculo,
        dados.get("codigo_roteiro") or dados.get("romaneio"),
        dados.get("descricao_rota"),
        dados.get("valor_coleta", 0),
        dados.get("quantidade_entregas", 0),
        dados.get("peso", 0),
        dados.get("volume", 0),
        dados.get("valor_carga", 0),
        km,
        pedagio,
        diaria,
        valor_final_frete,
        id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "valor_calculado": valor_final_frete
    })


# DELETE
@app.route("/api/rotas/<int:id>", methods=["DELETE"])
@app.route("/api/roteiros/<int:id>", methods=["DELETE"])
@app.route("/api/fretes/<int:id>", methods=["DELETE"])
def delete_rota(id):
    conn = get_db()
    conn.execute("DELETE FROM rotas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# ==================================
# API: CANHOTOS
# ==================================

@app.route("/api/canhotos", methods=["GET"])
def get_canhotos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM canhotos").fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/canhotos", methods=["POST"])
def add_canhoto():
    dados = request.json
    conn = get_db()

    conn.execute("""
        INSERT INTO canhotos (
            nota_fiscal,
            cliente,
            carga,
            data_entrega,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        dados.get("nota_fiscal"),
        dados.get("cliente"),
        dados.get("carga"),
        dados.get("data_entrega"),
        dados.get("status", "Pendente")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"}), 201

@app.route("/api/canhotos/<int:id>", methods=["DELETE"])
def delete_canhoto(id):
    conn = get_db()
    conn.execute("DELETE FROM canhotos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ==================================
# API: DEVOLUÇÕES (CRUD COMPLETO)
# ==================================

@app.route("/api/devolucoes", methods=["GET"])
def get_devolucoes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM devolucoes").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/devolucoes", methods=["POST"])
def add_devolucao():
    dados = request.json
    conn = get_db()

    conn.execute("""
        INSERT INTO devolucoes (
            nota_fiscal,
            cliente,
            motivo,
            data,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        dados.get("nota_fiscal"),
        dados.get("cliente"),
        dados.get("motivo"),
        dados.get("data"),
        dados.get("status", "Pendente")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"}), 201


@app.route("/api/devolucoes/<int:id>", methods=["PUT"])
def update_devolucao(id):
    dados = request.json
    conn = get_db()

    conn.execute("""
        UPDATE devolucoes
        SET
            nota_fiscal = ?,
            cliente = ?,
            motivo = ?,
            data = ?,
            status = ?
        WHERE id = ?
    """, (
        dados.get("nota_fiscal"),
        dados.get("cliente"),
        dados.get("motivo"),
        dados.get("data"),
        dados.get("status"),
        id
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@app.route("/api/devolucoes/<int:id>", methods=["DELETE"])
def delete_devolucao(id):
    conn = get_db()
    conn.execute("DELETE FROM devolucoes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# ==================================
# INTEGRAÇÃO: PROCESSAMENTO DE IMAGEM (OCR)
# ==================================

@app.route("/api/processar-imagem", methods=["POST"])
def processar_imagem():
    if "imagem" not in request.files:
        return jsonify({"erro": "Nenhuma imagem enviada"}), 400

    arquivo_imagem = request.files["imagem"]

    if arquivo_imagem.filename == "":
        return jsonify({"erro": "Arquivo inválido"}), 400

    try:
        imagem = Image.open(arquivo_imagem)
        texto_extraido = pytesseract.image_to_string(imagem, lang="por")

        padrao_nf = re.search(
            r"(?:nota|nf|nº|numero|número)[:.\s\-]+(\d+)",
            texto_extraido,
            re.IGNORECASE
        )
        nota_fiscal = padrao_nf.group(1) if padrao_nf else ""

        padrao_valor = re.search(
            r"(?:total|valor|r\$)[:\s\-]+([\d.,]+)",
            texto_extraido,
            re.IGNORECASE
        )
        valor_total = padrao_valor.group(1) if padrao_valor else ""

        padrao_cliente = re.search(
            r"(?:cliente|destinatario|razão social)[:\s\-]+([A-Za-z0-9\s]+)",
            texto_extraido,
            re.IGNORECASE
        )
        cliente = padrao_cliente.group(1).strip() if padrao_cliente else ""

        return jsonify({
            "status": "sucesso",
            "dados_sugeridos": {
                "nota_fiscal": nota_fiscal,
                "cliente": cliente,
                "valor_total": valor_total
            },
            "texto_completo_identificado": texto_extraido
        })

    except Exception as e:
        return jsonify({
            "erro": f"Falha no processamento: {str(e)}"
        }), 500


# ==================================
# EMISSÃO DE PDF ADAPTADO (NOVA TABELA)
# ==================================

@app.route("/relatorio/intervalo/pdf")
def relatorio_pdf():
    inicio = request.args.get("inicio") or "2000-01-01"
    fim = request.args.get("fim") or "2100-12-31"

    conn = get_db()

    rotas = conn.execute(
        "SELECT * FROM rotas WHERE data_carga BETWEEN ? AND ?",
        (inicio, fim)
    ).fetchall()

    canhotos = conn.execute(
        "SELECT * FROM canhotos WHERE data_entrega BETWEEN ? AND ?",
        (inicio, fim)
    ).fetchall()

    devolucoes = conn.execute(
        "SELECT * FROM devolucoes WHERE data BETWEEN ? AND ?",
        (inicio, fim)
    ).fetchall()

    resumo_motoristas = conn.execute("""
        SELECT
            motorista,
            COUNT(*) AS viagens,
            SUM(valor_frete) AS total
        FROM rotas
        WHERE data_carga BETWEEN ? AND ?
        GROUP BY motorista
        ORDER BY total DESC
    """, (inicio, fim)).fetchall()

    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(
        50,
        y,
        f"Relatório Logístico {inicio} até {fim}"
    )

    y -= 40

    def bloco(titulo, dados, texto):
        nonlocal y

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, titulo)

        y -= 20

        pdf.setFont("Helvetica", 10)

        for d in dados:
            pdf.drawString(50, y, texto(d))
            y -= 15

            if y < 50:
                pdf.showPage()
                y = 800

        y -= 10

    bloco(
        "MOVIMENTAÇÃO DE ROTAS E FRETES",
        rotas,
        lambda r: (
            f"Carga: {r['carga']} | "
            f"{r['motorista']} | "
            f"{r['descricao_rota']} | "
            f"Frete: R$ {r['valor_frete']:.2f}"
        )
    )

    bloco(
        "CANHOTOS DE NOTAS",
        canhotos,
        lambda c: (
            f"NF: {c['nota_fiscal']} | "
            f"Carga: {c['carga']} | "
            f"Status: {c['status']}"
        )
    )

    bloco(
        "DEVOLUÇÕES CONSTATADAS",
        devolucoes,
        lambda d: (
            f"NF: {d['nota_fiscal']} | "
            f"Motivo: {d['motivo']} | "
            f"{d['status']}"
        )
    )

    if y < 150:
        pdf.showPage()
        y = 800

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(
        50,
        y,
        "FECHAMENTO FINANCEIRO POR MOTORISTA"
    )

    y -= 25

    total_geral = 0

    pdf.setFont("Helvetica", 10)

    for r in resumo_motoristas:
        total_geral += r["total"] if r["total"] else 0

        pdf.drawString(
            50,
            y,
            f"{r['motorista']} | "
            f"Viagens: {r['viagens']} | "
            f"Total Faturado: R$ {r['total']:.2f}"
        )

        y -= 15

    y -= 15

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(
        50,
        y,
        f"TOTAL GERAL DO PERÍODO: R$ {total_geral:.2f}"
    )

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        download_name=f"relatorio_{inicio}_{fim}.pdf",
        as_attachment=True
    )

@app.route("/api/ocr", methods=["POST"])
def ocr_route():
    if "file" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files["file"]
    
    try:
        # 1. Converter o ficheiro enviado para algo que o OpenCV entenda
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"erro": "Imagem inválida"}), 400

        # 2. Pipeline de Processamento (limpeza da imagem)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Correção de iluminação com CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        processed = clahe.apply(gray)
        
        # Binarização Otsu para contraste máximo
        _, binary = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. Executar o OCR
        # O psm 6 assume um bloco único de texto (ideal para documentos)
        config = "--psm 6"
        texto = pytesseract.image_to_string(binary, lang='por', config=config)
        
        print(f"--- LOG DE OCR ---\n{texto}\n-------------------")
        
        # 4. Regex (Otimizado)
        # Nota: captura números de 5 a 9 dígitos após 'Nota', 'NF', 'Nº'
        nf_match = re.search(r'(?:Nota|NF|N[oº]|Romaneio)[:.\s]+(\d{5,9})', texto, re.IGNORECASE)
        
        # Cliente: Captura o que estiver após 'Cliente:' até a quebra de linha
        cliente_match = re.search(r'(?:Cliente|Destinatário)[:.\s]+([^\n\r]+)', texto, re.IGNORECASE)
        
        dados = {
            "nota_fiscal": nf_match.group(1) if nf_match else "NÃO IDENTIFICADO",
            "cliente": cliente_match.group(1).strip() if cliente_match else "NÃO IDENTIFICADO"
        }
        
        return jsonify({"sucesso": True, "dados": dados})

    except Exception as e:
        print(f"ERRO CRÍTICO NO OCR: {str(e)}")
        return jsonify({"erro": str(e)}), 500
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))