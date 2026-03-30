#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Limpeza de Arquivos Temporários no Windows

Remove arquivos e pastas de locais comuns de temporários:
    - Pasta TEMP do usuário (%TEMP%)
    - C:\Windows\Temp
    - C:\Windows\Prefetch

Arquivos em uso ou sem permissão são ignorados e contabilizados como erros.
Exibe estatísticas de remoção, erros e espaço liberado.

Uso:
    Execute como administrador para melhores resultados.
    python temp_cleaner.py

Autor: [Seu Nome]
Licença: MIT (ou outra de sua escolha)
"""

import os
import shutil
import platform
from pathlib import Path
from typing import Tuple


def validar_windows() -> None:
    """
    Verifica se o sistema operacional é Windows.

    Levanta:
        RuntimeError: se o sistema não for Windows.
    """
    if platform.system() != "Windows":
        raise RuntimeError("Este script é exclusivo para Windows.")


def obter_temp_usuario() -> Path:
    """
    Obtém o caminho da pasta TEMP do usuário a partir da variável de ambiente %TEMP%.

    Retorna:
        Path: caminho da pasta temporária.

    Levanta:
        RuntimeError: se a variável TEMP não estiver definida.
    """
    temp = os.getenv("TEMP")
    if not temp:
        raise RuntimeError("Variável de ambiente TEMP não encontrada.")
    return Path(temp)


def calcular_tamanho(pasta: Path) -> int:
    """
    Calcula o tamanho total de uma pasta (soma de todos os arquivos) em bytes.

    Args:
        pasta (Path): diretório a ser calculado.

    Returns:
        int: tamanho total em bytes. Arquivos sem permissão são ignorados.
    """
    total = 0
    for item in pasta.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except (PermissionError, OSError):
            # Ignora arquivos/pastas sem acesso
            continue
    return total


def limpar_pasta(pasta: Path) -> Tuple[int, int, int]:
    """
    Remove todos os itens (arquivos, links simbólicos e subpastas) de uma pasta.

    Args:
        pasta (Path): diretório a ser limpo.

    Returns:
        Tuple[int, int, int]: (itens removidos, erros, bytes liberados)

    Observações:
        - Se a pasta não existir, retorna (0, 0, 0).
        - Itens em uso ou sem permissão são ignorados e contam como erro.
        - Para pastas, usa shutil.rmtree (remove recursivamente).
    """
    removidos = 0
    erros = 0
    bytes_liberados = 0

    if not pasta.exists():
        return 0, 0, 0

    for item in pasta.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                # Arquivo ou link simbólico
                tamanho = item.stat().st_size
                item.unlink()  # remove
                removidos += 1
                bytes_liberados += tamanho

            elif item.is_dir():
                # Pasta: calcula tamanho antes de remover
                tamanho = calcular_tamanho(item)
                shutil.rmtree(item)
                removidos += 1
                bytes_liberados += tamanho

        except (PermissionError, OSError):
            # Arquivo/pasta em uso ou sem permissão
            erros += 1
            continue

    return removidos, erros, bytes_liberados


def formatar_mb(valor: int) -> str:
    """
    Converte bytes para megabytes com duas casas decimais.

    Args:
        valor (int): tamanho em bytes.

    Returns:
        str: string no formato "X.XX MB"
    """
    return f"{valor / (1024 * 1024):.2f} MB"


def main() -> None:
    """
    Função principal:
        - Verifica ambiente Windows.
        - Define as pastas a limpar.
        - Executa a limpeza e acumula estatísticas.
        - Exibe relatório final.
    """
    validar_windows()

    # Lista de pastas temporárias comuns no Windows
    pastas = [
        obter_temp_usuario(),
        Path(r"C:\Windows\Temp"),
        Path(r"C:\Windows\Prefetch"),
    ]

    total_removidos = 0
    total_erros = 0
    total_bytes = 0

    for pasta in pastas:
        print(f"\nLimpando: {pasta}")

        removidos, erros, bytes_liberados = limpar_pasta(pasta)

        total_removidos += removidos
        total_erros += erros
        total_bytes += bytes_liberados

        print(f"Removidos: {removidos}")
        print(f"Ignorados (em uso/permissão): {erros}")
        print(f"Espaço liberado: {formatar_mb(bytes_liberados)}")

    print("\n===== RESUMO FINAL =====")
    print(f"Total removido: {total_removidos}")
    print(f"Total ignorado: {total_erros}")
    print(f"Total liberado: {formatar_mb(total_bytes)}")


if __name__ == "__main__":
    main()