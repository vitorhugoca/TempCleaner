#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
temp_cleaner.py - Utilitário para limpeza de arquivos temporários no Windows.

Remove arquivos e pastas dos seguintes locais:
    - Pasta TEMP do usuário (obtida da variável de ambiente %TEMP%)
    - Temp
    - Prefetch

Arquivos em uso ou sem permissão são ignorados e contabilizados como erros.
Exibe estatísticas de remoção, erros e espaço liberado.

Uso:
    Execute o script diretamente (como administrador para melhores resultados).
"""

import os
import shutil
import platform
from pathlib import Path
from typing import Tuple


def validar_windows() -> None:
    """
    Verifica se o sistema operacional é Windows.

    Raises:
        RuntimeError: se o sistema não for Windows.
    """
    if platform.system() != "Windows":
        raise RuntimeError("Este script é exclusivo para Windows.")


def obter_temp_usuario() -> Path:
    """
    Obtém o caminho da pasta TEMP do usuário a partir da variável de ambiente.

    Returns:
        Path: caminho da pasta temporária.

    Raises:
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
        int: tamanho total em bytes. Ignora arquivos sem permissão ou erros de acesso.
    """
    total = 0
    # rglob('*') percorre recursivamente todos os arquivos e subpastas
    for item in pasta.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except (PermissionError, OSError):
            # Arquivos sem permissão são ignorados na contagem de tamanho
            continue
    return total


def limpar_pasta(pasta: Path) -> Tuple[int, int, int]:
    """
    Remove todos os itens (arquivos e subpastas) de uma pasta.

    Args:
        pasta (Path): diretório a ser limpo.

    Returns:
        Tuple[int, int, int]: (número de itens removidos, número de erros, bytes liberados)

    Observações:
        - Se a pasta não existir, retorna (0, 0, 0).
        - Para arquivos em uso ou sem permissão, ocorre erro (PermissionError/OSError)
          e o item é ignorado, incrementando o contador de erros.
        - Para pastas, utiliza shutil.rmtree, que pode falhar se houver arquivos em uso
          ou sem permissão; nesse caso, a exceção é capturada e contada como erro.
    """
    removidos = 0
    erros = 0
    bytes_liberados = 0

    if not pasta.exists():
        return 0, 0, 0

    # Itera sobre os itens imediatos (não recursivo)
    for item in pasta.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                # Obtém tamanho antes de remover
                tamanho = item.stat().st_size
                item.unlink()  # remove arquivo ou symlink
                removidos += 1
                bytes_liberados += tamanho

            elif item.is_dir():
                # Calcula tamanho total da pasta antes de removê-la
                tamanho = calcular_tamanho(item)
                shutil.rmtree(item)  # remove a pasta e todo seu conteúdo
                removidos += 1
                bytes_liberados += tamanho

        except (PermissionError, OSError):
            # Arquivo/pasta em uso, sem permissão ou outro erro de sistema
            erros += 1
            continue

    return removidos, erros, bytes_liberados


def formatar_mb(valor: int) -> str:
    """
    Formata um valor em bytes para megabytes (MB) com duas casas decimais.

    Args:
        valor (int): tamanho em bytes.

    Returns:
        str: string formatada (ex.: "15.34 MB")
    """
    return f"{valor / (1024 * 1024):.2f} MB"


def main() -> None:
    """
    Função principal:
        - Valida sistema operacional.
        - Define lista de pastas a serem limpas.
        - Para cada pasta, executa a limpeza e acumula estatísticas.
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