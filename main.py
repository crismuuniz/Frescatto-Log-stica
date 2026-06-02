import os
import io
import sqlite3
import pandas as pd

from flask import Flask, request, jsonify, render_template, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

app = Flask(__name__)

# ==================================
# SQLITE CONFIGURAÇÃO
# ==================================

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fretes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rota TEXT,
        placa TEXT,
        data TEXT,
        romaneio TEXT,
        peso REAL,
        modelo_veiculo TEXT,
        tipo_veiculo TEXT,
        acrescimo REAL,
        transportadora TEXT,
        mes_referencia TEXT,
        valor_total REAL,
        quantidade_entregas INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canhotos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nota_fiscal TEXT,
        cliente TEXT,
        rota TEXT,
        carga TEXT,
        data_entrega TEXT,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roteiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        motorista TEXT,
        veiculo TEXT,
        data_saida TEXT,
        codigo_roteiro TEXT,
        destinos TEXT
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

    # Criação da tabela auxiliar usada no cálculo financeiro para evitar erros de Join
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabela_roteiros (
        codigo TEXT PRIMARY KEY,
        valor_fiorino REAL DEFAULT 0,
        valor_bongo REAL DEFAULT 0,
        valor_hr REAL DEFAULT 0,
        valor_34 REAL DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


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

    canhotos = conn.execute("SELECT * FROM canhotos").fetchall()
    fretes = conn.execute("SELECT * FROM fretes").fetchall()
    roteiros = conn.execute("SELECT * FROM roteiros").fetchall()
    devolucoes = conn.execute("SELECT * FROM devolucoes").fetchall()

    conn.close()

    return render_template(
        "relatorios.html",
        data="Relatório geral",
        canhotos=canhotos,
        fretes=fretes,
        roteiros=roteiros,
        devolucoes=devolucoes
    )

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
        INSERT INTO canhotos (nota_fiscal, cliente, rota, carga, data_entrega, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        dados.get("nota_fiscal"),
        dados.get("cliente"),
        dados.get("rota"),
        dados.get("carga"),
        dados.get("data_entrega"),
        dados.get("status", "Recebido")
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201

# ==================================
# API: FRETES
# ==================================

@app.route("/api/fretes", methods=["GET"])
def get_fretes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM fretes").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/fretes", methods=["POST"])
def add_frete():
    dados = request.json
    conn = get_db()
    conn.execute("""
        INSERT INTO fretes (
            rota, placa, data, romaneio, peso,
            modelo_veiculo, tipo_veiculo, acrescimo,
            transportadora, mes_referencia, valor_total, quantidade_entregas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get("rota"),
        dados.get("placa"),
        dados.get("data"),
        dados.get("romaneio"),
        dados.get("peso"),
        dados.get("modelo_veiculo"),
        dados.get("tipo_veiculo"),
        dados.get("acrescimo", 0),
        dados.get("transportadora"),
        dados.get("mes_referencia"),
        dados.get("valor_total"),
        dados.get("quantidade_entregas")
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201

# ==================================
# API: ROTEIROS
# ==================================

@app.route("/api/roteiros", methods=["GET"])
def get_roteiros():
    conn = get_db()
    rows = conn.execute("SELECT * FROM roteiros").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/roteiros", methods=["POST"])
def add_roteiro():
    dados = request.json
    conn = get_db()
    conn.execute("""
        INSERT INTO roteiros (
            motorista, veiculo, data_saida, codigo_roteiro, destinos
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        dados.get("motorista"),
        dados.get("veiculo"),
        dados.get("data_saida"),
        dados.get("codigo_roteiro"),
        dados.get("destinos")
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201

# ==================================
# API: DEVOLUÇÕES
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
        INSERT INTO devolucoes (nota_fiscal, cliente, motivo, data, status)
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

# ==================================
# EMISSÃO DE PDF POR INTERVALO
# ==================================

@app.route("/relatorio/intervalo/pdf")
def relatorio_pdf():
    inicio = request.args.get("inicio") or "2000-01-01"
    fim = request.args.get("fim") or "2100-12-31"

    conn = get_db()

    canhotos = conn.execute("SELECT * FROM canhotos WHERE data_entrega BETWEEN ? AND ?", (inicio, fim)).fetchall()
    fretes = conn.execute("SELECT * FROM fretes WHERE data BETWEEN ? AND ?", (inicio, fim)).fetchall()
    roteiros = conn.execute("SELECT * FROM roteiros WHERE data_saida BETWEEN ? AND ?", (inicio, fim)).fetchall()
    devolucoes = conn.execute("SELECT * FROM devolucoes WHERE data BETWEEN ? AND ?", (inicio, fim)).fetchall()

    resumo_motoristas = conn.execute("""
        SELECT
            r.motorista,
            COUNT(*) AS viagens,
            COALESCE(
                SUM(
                    CASE
                        WHEN LOWER(r.veiculo) LIKE '%fiorino%' THEN t.valor_fiorino
                        WHEN LOWER(r.veiculo) LIKE '%bongo%' THEN t.valor_bongo
                        WHEN LOWER(r.veiculo) LIKE '%hr%' THEN t.valor_hr
                        WHEN LOWER(r.veiculo) LIKE '%3/4%' THEN t.valor_34
                        WHEN LOWER(r.veiculo) LIKE '%34%' THEN t.valor_34
                        ELSE 0
                    END
                ),
                0
            ) AS total
        FROM roteiros r
        LEFT JOIN tabela_roteiros t ON r.codigo_roteiro = t.codigo
        WHERE r.data_saida BETWEEN ? AND ?
        GROUP BY r.motorista
        ORDER BY total DESC
    """, (inicio, fim)).fetchall()

    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"Relatório {inicio} até {fim}")
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

    bloco("CANHOTOS", canhotos, lambda c: f"NF {c['nota_fiscal']} | {c['cliente']} | {c['rota']}")
    bloco("FRETES", fretes, lambda f: f"{f['rota']} | {f['placa']} | R$ {f['valor_total']}")
    bloco("ROTEIROS", roteiros, lambda r: f"{r['motorista']} | {r['veiculo']} | Rota {r['codigo_roteiro']} | {r['data_saida']}")
    bloco("DEVOLUÇÕES", devolucoes, lambda d: f"{d['nota_fiscal']} | {d['motivo']} | {d['status']}")

    if y < 150:
        pdf.showPage()
        y = 800

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "RESUMO FINANCEIRO POR MOTORISTA")
    y -= 25

    pdf.setFont("Helvetica", 10)
    total_geral = 0

    for r in resumo_motoristas:
        total_geral += r["total"]
        pdf.drawString(
            50, y,
            f"{r['motorista']} | Viagens: {r['viagens']} | Total: R$ {r['total']:.2f}"
        )
        y -= 15
        if y < 50:
            pdf.showPage()
            y = 800

    y -= 15
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, f"TOTAL GERAL DOS ROTEIROS: R$ {total_geral:.2f}")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        download_name=f"relatorio_{inicio}_{fim}.pdf",
        as_attachment=True
    )



# ==================================
# GERAÇÃO DO EXCEL COMPLETO (VERSÃO CORRIGIDA)
# ==================================

# ==================================
# GERAÇÃO DO EXCEL PREMIUM ESTILIZADO
# ==================================

@app.route("/relatorio/intervalo/excel")
def relatorio_excel():
    inicio = request.args.get("inicio") or "2000-01-01"
    fim = request.args.get("fim") or "2100-12-31"

    # Formatando as datas para exibição amigável (DD/MM/AAAA)
    try:
        data_ini_pt = f"{inicio[8:10]}/{inicio[5:7]}/{inicio[0:4]}"
        data_fim_pt = f"{fim[8:10]}/{fim[5:7]}/{fim[0:4]}"
    except:
        data_ini_pt, data_fim_pt = inicio, fim

    conn = get_db()

    # Queries de busca no banco
    c_rows = conn.execute("SELECT id, nota_fiscal, cliente, rota, carga, data_entrega, status FROM canhotos WHERE data_entrega BETWEEN ? AND ?", (inicio, fim)).fetchall()
    f_rows = conn.execute("SELECT id, rota, placa, data, romaneio, peso, modelo_veiculo, tipo_veiculo, acrescimo, transportadora, mes_referencia, valor_total, quantidade_entregas FROM fretes WHERE data BETWEEN ? AND ?", (inicio, fim)).fetchall()
    r_rows = conn.execute("SELECT id, motorista, veiculo, data_saida, codigo_roteiro, destinos FROM roteiros WHERE data_saida BETWEEN ? AND ?", (inicio, fim)).fetchall()
    d_rows = conn.execute("SELECT id, nota_fiscal, cliente, motivo, data, status FROM devolucoes WHERE data BETWEEN ? AND ?", (inicio, fim)).fetchall()
    
    m_rows = conn.execute("""
        SELECT r.motorista, COUNT(*) AS viagens,
               COALESCE(SUM(CASE 
                    WHEN LOWER(r.veiculo) LIKE '%fiorino%' THEN t.valor_fiorino
                    WHEN LOWER(r.veiculo) LIKE '%bongo%' THEN t.valor_bongo
                    WHEN LOWER(r.veiculo) LIKE '%hr%' THEN t.valor_hr
                    WHEN LOWER(r.veiculo) LIKE '%3/4%' THEN t.valor_34
                    WHEN LOWER(r.veiculo) LIKE '%34%' THEN t.valor_34
                    ELSE 0 END), 0) AS total
        FROM roteiros r
        LEFT JOIN tabela_roteiros t ON r.codigo_roteiro = t.codigo
        WHERE r.data_saida BETWEEN ? AND ?
        GROUP BY r.motorista
        ORDER BY total DESC
    """, (inicio, fim)).fetchall()

    conn.close()

    # Conversão e definição de colunas bonitas para exibição no Excel (Letras Maiúsculas)
    df_canhotos = pd.DataFrame([dict(r) for r in c_rows]) if c_rows else pd.DataFrame(columns=["ID", "NOTA FISCAL", "CLIENTE", "ROTA", "CARGA", "DATA ENTREGA", "STATUS"])
    if c_rows: df_canhotos.columns = ["ID", "NOTA FISCAL", "CLIENTE", "ROTA", "CARGA", "DATA ENTREGA", "STATUS"]

    df_fretes = pd.DataFrame([dict(r) for r in f_rows]) if f_rows else pd.DataFrame(columns=["ID", "ROTA", "PLACA", "DATA", "ROMANEIO", "PESO (KG)", "MODELO", "TIPO", "ACRÉSCIMO", "TRANSPORTADORA", "MÊS REF", "VALOR TOTAL", "ENTREGAS"])
    if f_rows: df_fretes.columns = ["ID", "ROTA", "PLACA", "DATA", "ROMANEIO", "PESO (KG)", "MODELO", "TIPO", "ACRÉSCIMO", "TRANSPORTADORA", "MÊS REF", "VALOR TOTAL", "ENTREGAS"]

    df_roteiros = pd.DataFrame([dict(r) for r in r_rows]) if r_rows else pd.DataFrame(columns=["ID", "MOTORISTA", "VEÍCULO", "DATA SAÍDA", "CÓDIGO ROTEIRO", "DESTINOS"])
    if r_rows: df_roteiros.columns = ["ID", "MOTORISTA", "VEÍCULO", "DATA SAÍDA", "CÓDIGO ROTEIRO", "DESTINOS"]

    df_devolucoes = pd.DataFrame([dict(r) for r in d_rows]) if d_rows else pd.DataFrame(columns=["ID", "NOTA FISCAL", "CLIENTE", "MOTIVO", "DATA", "STATUS"])
    if d_rows: df_devolucoes.columns = ["ID", "NOTA FISCAL", "CLIENTE", "MOTIVO", "DATA", "STATUS"]

    df_resumo = pd.DataFrame([dict(r) for r in m_rows]) if m_rows else pd.DataFrame(columns=["MOTORISTA", "QTD VIAGENS", "TOTAL FATURADO"])
    if m_rows: df_resumo.columns = ["MOTORISTA", "QTD VIAGENS", "TOTAL FATURADO"]

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="openpyxl")
    
    # 1. CRIANDO A ABA DE CAPA (HOME)
    df_capa = pd.DataFrame()
    df_capa.to_excel(writer, sheet_name="Painel Frescatto", index=False)
    
    # Escrevendo as abas de dados normais
    df_canhotos.to_excel(writer, sheet_name="Canhotos", index=False)
    df_fretes.to_excel(writer, sheet_name="Fretes", index=False)
    df_roteiros.to_excel(writer, sheet_name="Roteiros", index=False)
    df_devolucoes.to_excel(writer, sheet_name="Devolucoes", index=False)
    df_resumo.to_excel(writer, sheet_name="Resumo Motoristas", index=False)

    workbook = writer.book

    # 2. ESTILIZANDO A ABA DA CAPA
    ws_capa = workbook["Painel Frescatto"]
    ws_capa.views.sheetView[0].showGridLines = True
    
    # Título Principal (Vermelho Frescatto)
    ws_capa["B3"] = "FECHAMENTO FRESCATTO POR PERÍODO"
    ws_capa["B3"].font = Font(name="Arial", size=18, bold=True, color="C00000") # Vermelho Escuro/Cardeal
    
    # Subtítulo com período informado
    ws_capa["B4"] = f"Período de Referência: {data_ini_pt} até {data_fim_pt}"
    ws_capa["B4"].font = Font(name="Arial", size=11, italic=True, color="595959")
    
    # Instruções de navegação internas
    ws_capa["B6"] = "📌 Use as abas na barra inferior do Excel para navegar entre os módulos organizados."
    ws_capa["B6"].font = Font(name="Arial", size=11, bold=True, color="333333")

    # 3. ESTILIZAÇÃO GERAL DAS ABAS DE DADOS
    for sheet_name in workbook.sheetnames:
        if sheet_name == "Painel Frescatto":
            continue
            
        ws = workbook[sheet_name]
        ws.views.sheetView[0].showGridLines = True # Garante que as linhas de grade continuem visíveis
        
        # Cabeçalhos elegantes: Grafite Escuro com Letra Branca
        if ws.max_row >= 1:
            for cell in ws[1]:
                cell.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="2F3542") # Dark Slate / Grafite
        
        # Linhas Alternadas (Efeito Zebra para facilitar leitura)
        for row_idx in range(2, ws.max_row + 1):
            cor_linha = "F1F2F6" if row_idx % 2 == 0 else "FFFFFF"
            for cell in ws[row_idx]:
                cell.font = Font(name="Arial", size=10)
                cell.fill = PatternFill(fill_type="solid", fgColor=cor_linha)
                
        # Formatação Numérica Automática para Moeda (R$) nas colunas financeiras
            do_titulo = str(ws.cell(row=1, column=cell.column).value).upper()
            if "VALOR" in do_titulo or "TOTAL" in do_titulo or "FATURADO" in do_titulo or "ACRÉSCIMO" in do_titulo:
                    if cell.value is not None:
                        try:
                            cell.value = float(cell.value)
                            cell.number_format = 'R$ #,##0.00'
                        except:
                            pass

        # Dimensionamento perfeito das larguras de colunas
        for column in ws.columns:
            valores = [len(str(cell.value or '')) for cell in column]
            tamanho = max(valores) if valores else 10
            coluna = get_column_letter(column[0].column)
            ws.column_dimensions[coluna].width = max(tamanho + 4, 13)

    writer.close()
    output.seek(0)
    
    return send_file(
        output, 
        download_name=f"Fechamento_Frescatto_{inicio}_a_{fim}.xlsx", 
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==================================
# API: CONTROLE EXCLUSÃO / EDIÇÃO
# ==================================

@app.route("/api/roteiros/<int:id>", methods=["DELETE"])
def delete_roteiro(id):
    conn = get_db()
    conn.execute("DELETE FROM roteiros WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/roteiros/<int:id>", methods=["PUT"])
def update_roteiro(id):
    dados = request.json
    conn = get_db()
    conn.execute("""
        UPDATE roteiros
        SET motorista = ?,
            veiculo = ?,
            data_saida = ?,
            codigo_roteiro = ?,
            destinos = ?
        WHERE id = ?
    """, (
        dados.get("motorista"),
        dados.get("veiculo"),
        dados.get("data_saida"),
        dados.get("codigo_roteiro"),
        dados.get("destinos"),
        id
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 3000)),
        debug=True
    )