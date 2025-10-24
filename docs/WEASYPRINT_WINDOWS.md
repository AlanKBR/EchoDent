# WeasyPrint no Windows (MSYS2)

Se você vê o aviso "WeasyPrint could not import some external libraries", instale as dependências nativas (Pango/Cairo) e aponte o caminho das DLLs.

Referência oficial: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation

## Passo a passo (PowerShell)

1) Instalar MSYS2
- Baixe e instale: https://www.msys2.org/#installation (opções padrão)

2) Instalar Pango (e deps) no shell do MSYS2
- Abra o atalho "MSYS2 MinGW x64"
- Rode:

```
pacman -S --noconfirm mingw-w64-x86_64-pango
```

3) Configurar variável de ambiente para o Python encontrar as DLLs
- No Windows, as DLLs ficam em `C:\msys64\mingw64\bin` por padrão.
- Adicione ao seu `.env` (ou ao ambiente do sistema):

```
WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
```

O arquivo `.env.example` já contém uma linha comentada com esse valor.

4) (Opcional) Verificar instalação
- Ative o seu venv e execute:

```
python -m weasyprint --info
```

Se tudo estiver correto, você verá informações sobre Pango e backends.

## Alternativas
- WSL: use o WeasyPrint como no Linux (instale `libpango` e afins).
- Executável: há um binário standalone em https://github.com/Kozea/WeasyPrint/releases (note os possíveis falsos positivos de antivírus conforme os autores).

## Dicas
- O projeto faz um bootstrap automático no `run.py`: se `WEASYPRINT_DLL_DIRECTORIES` não for definido e `C:\msys64\mingw64\bin` existir, ele define essa variável para você.
- Se você instalou o MSYS2 em outro diretório, ajuste o caminho no `.env`.
