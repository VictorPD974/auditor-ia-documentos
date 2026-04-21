# Auditor de Documentos Inteligente - NLConsulting

Este projeto foi desenvolvido como parte do processo seletivo para a NLConsulting. O sistema realiza a extração de dados de documentos fiscais (.txt) em larga escala, utilizando Inteligência Artificial para identificar anomalias e estruturar dados para Business Intelligence.

##  Tecnologias Utilizadas
- **Linguagem:** Python 3.x
- **IA:** Llama 3.3 70B via Groq API (Extração e Estruturação de Dados)
- **Performance:** Multithreading com `ThreadPoolExecutor` para processamento paralelo.
- **Análise de Dados:** Pandas para geração de logs e bases CSV.

##  Diferenciais Técnicos e Performance
- **Escalabilidade:** Implementação de processamento paralelo que otimizou o tempo de execução de 1.000 documentos de 16 minutos para menos de 2 minutos.
- **Resiliência:** Configuração de um mecanismo de *throttle* (0.4s) para conformidade estrita com os Rate Limits das APIs, evitando erros 429.
- **Motor de Auditoria:** Detecção automatizada de duplicidades, inconsistências temporais e conformidade de aprovadores.

##  Entregáveis do Sistema
O sistema gera automaticamente os ficheiros necessários para a tomada de decisão:
1. `resultados_bi.csv`: Base de dados limpa e tipada para integração com Power BI.
2. `log_auditoria.csv`: Registo detalhado de anomalias com níveis de confiança (Médio/Alto).

##  Como Executar
1. Clone este repositório.
2. Configure a sua `GROQ_API_KEY` num ficheiro `.env`.
3. Instale as dependências: `pip install -r requirements.txt`.
4. Execute o sistema: `python main.py`.
