import os
import zipfile
import chardet
import requests
import json
import time
import re
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Carrega as chaves de API do ficheiro .env
load_dotenv()


class AuditorIA:
    """
    Sistema de Auditoria Inteligente - NLConsulting
    Implementa extração via IA (LLM), processamento paralelo e detecção de anomalias.
    """

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Regra de Negócio: Aprovadores autorizados conforme briefing
        self.aprovadores_oficiais = ["Maria Silva", "João Souza", "Ana Costa"]

    def tratar_encoding(self, binario):
        """Garante a leitura correta de ficheiros com diferentes encodings (ex: ANSI, UTF-8)"""
        deteccao = chardet.detect(binario)
        encoding = deteccao['encoding'] or 'utf-8'
        return binario.decode(encoding, errors='ignore')

    def validar_e_limpar_dados(self, dados):
        """Auditoria Sintética: Normaliza campos para processamento matemático e BI"""
        # Limpa CNPJ: apenas números
        dados['CNPJ_FORNECEDOR'] = re.sub(r'\D', '', str(dados.get('CNPJ_FORNECEDOR', '')))

        # Limpa Valor: Converte para float (ex: R$ 1.250,00 -> 1250.0)
        valor_raw = str(dados.get('VALOR_BRUTO', '0'))
        try:
            valor_limpo = valor_raw.replace('R$', '').replace('.', '').replace(',', '.').strip()
            dados['VALOR_BRUTO'] = float(re.sub(r'[^\d.]', '', valor_limpo))
        except:
            dados['VALOR_BRUTO'] = 0.0
        return dados

    def extrair_com_ia(self, texto):
        """Interface com a API Groq (Llama 3.3 70B) para extração de dados estruturados"""
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um auditor fiscal. Extraia dados e responda APENAS em JSON puro."
                },
                {
                    "role": "user",
                    "content": (
                        "Extraia os campos: TIPO_DOCUMENTO, NUMERO_DOCUMENTO, DATA_EMISSAO_NF, "
                        "FORNECEDOR, CNPJ_FORNECEDOR, VALOR_BRUTO, DATA_PAGAMENTO, APROVADO_POR, STATUS. "
                        f"Texto: {texto}"
                    )
                }
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=30)
            if response.status_code == 200:
                conteudo = response.json()['choices'][0]['message']['content']
                return self.validar_e_limpar_dados(json.loads(conteudo))
            return {"erro": f"API Status {response.status_code}"}
        except Exception as e:
            return {"erro": str(e)}

    def processar_arquivo_individual(self, zip_content, filename):
        """Worker individual para processamento em thread"""
        try:
            # O zip_content deve ser o objeto ZipFile aberto
            with zip_content.open(filename) as f:
                texto = self.tratar_encoding(f.read())

            dados = self.extrair_com_ia(texto)
            dados['arquivo_origem'] = filename
            dados['data_processamento'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Rate Limiting: 0.5s por thread garante estabilidade na cota gratuita
            time.sleep(0.4)
            return dados
        except Exception as e:
            return {"arquivo_origem": filename, "erro": str(e)}

    def detectar_anomalias_lote(self, lista_resultados):
        """Motor de Regras: Identifica fraudes e erros nos 1.000 documentos"""
        for i, nota in enumerate(lista_resultados):
            if "erro" in nota: continue

            anomalias = []

            # 1. Verificação de Duplicidade
            for j, outra in enumerate(lista_resultados):
                if i != j and nota.get('NUMERO_DOCUMENTO') == outra.get('NUMERO_DOCUMENTO') \
                        and nota.get('FORNECEDOR') == outra.get('FORNECEDOR'):
                    anomalias.append(
                        {"regra": "NF duplicada", "evidencia": nota['NUMERO_DOCUMENTO'], "confianca": "Alto"})
                    break

            # 2. Inconsistência Temporal (Emissão > Pagamento)
            try:
                dt_em = datetime.strptime(nota.get('DATA_EMISSAO_NF', ''), '%d/%m/%Y')
                dt_pg = datetime.strptime(nota.get('DATA_PAGAMENTO', ''), '%d/%m/%Y')
                if dt_em > dt_pg:
                    anomalias.append({"regra": "NF emitida após pagamento",
                                      "evidencia": f"E:{nota['DATA_EMISSAO_NF']} P:{nota['DATA_PAGAMENTO']}",
                                      "confianca": "Alto"})
            except:
                pass

            # 3. Compliance de Aprovação
            if nota.get('APROVADO_POR') not in self.aprovadores_oficiais:
                anomalias.append(
                    {"regra": "Aprovador não reconhecido", "evidencia": nota.get('APROVADO_POR'), "confianca": "Médio"})

            # 4. Conflito de Status
            if nota.get('STATUS') == 'CANCELADO' and nota.get('DATA_PAGAMENTO'):
                anomalias.append(
                    {"regra": "STATUS inconsistente", "evidencia": "Cancelado com pagamento", "confianca": "Médio"})

            nota['anomalias'] = anomalias
            nota['tem_anomalia'] = len(anomalias) > 0

    def gerar_entregaveis(self, resultados):
        """Gera os ficheiros CSV para Power BI e Auditoria (Requisito Eliminatório)"""
        # Base para Dashboard
        df_bi = pd.DataFrame(resultados).drop(columns=['anomalias'], errors='ignore')
        df_bi.to_csv('resultados_bi.csv', index=False, sep=';', encoding='utf-8-sig')

        # Log de Auditoria Detalhado
        log_data = []
        for n in resultados:
            for a in n.get('anomalias', []):
                log_data.append({
                    "arquivo": n.get('arquivo_origem'),
                    "timestamp": n.get('data_processamento'),
                    "regra": a['regra'],
                    "evidencia": a['evidencia'],
                    "confianca": a['confianca']
                })
        pd.DataFrame(log_data).to_csv('log_auditoria.csv', index=False, sep=';', encoding='utf-8-sig')
        print("✅ Ficheiros 'resultados_bi.csv' e 'log_auditoria.csv' prontos!")

    def processar_zip(self, zip_path):
        """Executa o processamento paralelo em escala (1.000 ficheiros)"""
        if not os.path.exists(zip_path):
            return [{"erro": "ZIP não encontrado"}]

        resultados_finais = []
        with zipfile.ZipFile(zip_path, 'r') as z:
            arquivos = [f for f in z.namelist() if f.endswith('.txt') and not f.startswith('__MACOSX')]
            total = len(arquivos)
            print(f"🚀 Iniciando Auditoria Paralela: {total} ficheiros.")

            # Multithreading: 5 workers processando em paralelo
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.processar_arquivo_individual, z, nome) for nome in arquivos]

                for i, future in enumerate(futures):
                    resultados_finais.append(future.result())
                    if (i + 1) % 50 == 0:
                        print(f"Progresso: {i + 1}/{total} concluídos...")

        self.detectar_anomalias_lote(resultados_finais)
        self.gerar_entregaveis(resultados_finais)
        return resultados_finais