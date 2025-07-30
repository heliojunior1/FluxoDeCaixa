import sys
import os

# Adicionar src ao PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("fluxocaixa.main:app", host="0.0.0.0", port=8000, reload=True)
