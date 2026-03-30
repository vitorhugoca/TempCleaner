#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
temp_cleaner.py - Limpeza segura de arquivos temporários no Windows

Remove arquivos e pastas de locais comuns de temporários:
    - %TEMP% do usuário
    - C:\Windows\Temp
    - C:\Windows\Prefetch (com confirmação)

Recursos adicionais:
    - Verificação de privilégios de administrador
    - Modo dry-run (apenas lista o que seria removido)
    - Suporte a pastas extras via linha de comando
    - Logging opcional
    - Tratamento refinado de erros (PermissionError vs FileNotFoundError)

Uso:
    python temp_cleaner.py [--dry-run] [--folders PASTA1 PASTA2] [--log ARQUIVO.log] [--yes]

Autor: [Seu Nome]
Licença: MIT
"""

import os
import shutil
import platform
import argparse
import logging
import ctypes
from pathlib import Path
from typing import List, Tuple, Optional


# ============================================================================
# CONFIGURAÇÕES E FUNÇÕES AUXILIARES
# ============================================================================

def is_admin() -> bool:
    """Retorna True se o processo tem privilégios de administrador no Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False  # Não Windows ou falha ao acessar


def formatar_mb(valor: int) -> str:
    """Converte bytes para megabytes (duas casas decimais)."""
    return f"{valor / (1024 * 1024):.2f} MB"


def configurar_logging(log_file: Optional[str] = None) -> None:
    """Configura o logging para console e opcionalmente para arquivo."""
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


# ============================================================================
# FUNÇÕES DE LIMPEZA
# ============================================================================

def limpar_pasta(pasta: Path, dry_run: bool = False, yes: bool = False) -> Tuple[int, int, int]:
    """
    Remove arquivos e subpastas de uma pasta.

    Args:
        pasta: Caminho da pasta a ser limpa.
        dry_run: Se True, apenas lista os itens que seriam removidos.
        yes: Se True, não pede confirmação para pastas sensíveis (Prefetch).

    Returns:
        (itens_removidos, erros, bytes_liberados)
    """
    if not pasta.exists():
        logging.info(f"Pasta não encontrada: {pasta}")
        return 0, 0, 0

    # Confirmação especial para Prefetch
    if pasta.name.lower() == "prefetch" and not yes:
        resposta = input(f"Limpar {pasta} pode reduzir desempenho inicial. Continuar? (s/N): ")
        if resposta.lower() != 's':
            logging.info(f"Limpeza de {pasta} cancelada pelo usuário.")
            return 0, 0, 0

    removidos = 0
    erros = 0
    bytes_liberados = 0

    logging.info(f"Processando: {pasta} (dry-run={dry_run})")

    for item in pasta.iterdir():
        try:
            if item.is_symlink() or item.is_file():
                # Arquivo ou link simbólico
                tamanho = item.stat().st_size
                if not dry_run:
                    item.unlink()
                removidos += 1
                bytes_liberados += tamanho
                logging.debug(f"Removeria: {item} ({formatar_mb(tamanho)})" if dry_run
                              else f"Removido: {item} ({formatar_mb(tamanho)})")

            elif item.is_dir():
                # Pasta: precisa calcular tamanho antes de remover (não podemos remover
                # e depois somar). Mesmo em dry-run, percorremos a árvore para contar.
                tamanho = 0
                # Contagem recursiva de tamanho (pode ser pesada, mas necessária)
                for root, dirs, files in os.walk(item):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            tamanho += fp.stat().st_size
                        except (PermissionError, OSError):
                            # Ignora arquivos sem acesso, contagem aproximada
                            pass
                if not dry_run:
                    shutil.rmtree(item, ignore_errors=False)
                removidos += 1
                bytes_liberados += tamanho
                logging.debug(f"Removeria pasta: {item} ({formatar_mb(tamanho)})" if dry_run
                              else f"Pasta removida: {item} ({formatar_mb(tamanho)})")

        except PermissionError:
            erros += 1
            logging.warning(f"Sem permissão para remover: {item}")
        except FileNotFoundError:
            # Item já foi removido por outro processo, ignorar
            logging.debug(f"Item não encontrado (já removido?): {item}")
        except OSError as e:
            erros += 1
            logging.error(f"Erro ao remover {item}: {e}")

    return removidos, erros, bytes_liberados


# ============================================================================
# FUNÇÕES PRINCIPAIS
# ============================================================================

def obter_pastas_padrao() -> List[Path]:
    """Retorna a lista de pastas padrão a serem limpas."""
    pastas = [Path(os.getenv("TEMP", ""))]
    if not pastas[0] or not pastas[0].exists():
        pastas[0] = Path(os.environ.get("TEMP", ""))
    pastas.append(Path(r"C:\Windows\Temp"))
    pastas.append(Path(r"C:\Windows\Prefetch"))
    # Remove pastas vazias ou inválidas
    return [p for p in pastas if p and str(p).strip()]


def main() -> None:
    """Função principal com parsing de argumentos e execução."""
    # Argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description="Limpeza de arquivos temporários no Windows."
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="Apenas lista os arquivos que seriam removidos (não executa remoção)"
    )
    parser.add_argument(
        '--folders', nargs='+', default=[],
        help="Pastas adicionais a serem limpas (forneça os caminhos)"
    )
    parser.add_argument(
        '--log', type=str, help="Arquivo para salvar log das operações"
    )
    parser.add_argument(
        '--yes', action='store_true',
        help="Responde 'sim' automaticamente para confirmações (ex.: Prefetch)"
    )
    args = parser.parse_args()

    # Configurar logging
    configurar_logging(args.log)

    # Verificar sistema operacional
    if platform.system() != "Windows":
        logging.error("Este script é exclusivo para Windows.")
        return

    # Verificar privilégios
    if not is_admin():
        logging.warning("Executando sem privilégios de administrador. "
                        "Pastas do sistema (Windows\\Temp, Prefetch) podem falhar.")

    # Definir pastas a processar
    pastas = obter_pastas_padrao()
    if args.folders:
        for folder in args.folders:
            pastas.append(Path(folder))

    # Remover duplicatas (preservando ordem)
    pastas_unicas = []
    for p in pastas:
        if p.resolve() not in [x.resolve() for x in pastas_unicas]:
            pastas_unicas.append(p)

    # Acumuladores
    total_removidos = 0
    total_erros = 0
    total_bytes = 0

    # Processar cada pasta
    for pasta in pastas_unicas:
        print(f"\n--- Limpando: {pasta} ---")
        removidos, erros, bytes_liberados = limpar_pasta(pasta, args.dry_run, args.yes)

        total_removidos += removidos
        total_erros += erros
        total_bytes += bytes_liberados

        print(f"Removidos: {removidos}")
        print(f"Ignorados (erros/permissão): {erros}")
        print(f"Espaço liberado: {formatar_mb(bytes_liberados)}")

    # Resumo final
    print("\n===== RESUMO FINAL =====")
    print(f"Total de itens processados: {total_removidos}")
    print(f"Total de erros: {total_erros}")
    print(f"Total liberado: {formatar_mb(total_bytes)}")

    if args.dry_run:
        print("\n(Modo dry-run – nenhuma alteração foi realizada.)")


if __name__ == "__main__":
    main()