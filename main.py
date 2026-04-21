from fastapi import FastAPI, UploadFile, File
from processor import AuditorIA
import os

app = FastAPI(title="Auditor NLC")
auditor = AuditorIA()

@app.post("/upload")
async def processar(file: UploadFile = File(...)):
    # Salva temporário
    content = await file.read()
    temp_path = "temp_notas.zip"
    with open(temp_path, "wb") as f:
        f.write(content)

    # Processa e retorna o resultado direto
    return auditor.processar_zip(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)