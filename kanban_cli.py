#!/usr/bin/env python3
"""
CLI para acompanhar o processo seletivo no Kanban.

Uso:
  python3 kanban_cli.py list [fase]
  python3 kanban_cli.py move <job_id_ou_prefixo> <fase> ["nota opcional"]
  python3 kanban_cli.py note <job_id_ou_prefixo> "texto da nota"
  python3 kanban_cli.py fases

Exemplos:
  python3 kanban_cli.py list
  python3 kanban_cli.py list entrevista
  python3 kanban_cli.py move a1b2c3d4 contato "Ligaram hoje as 14h, entrevista marcada pra sexta"
  python3 kanban_cli.py move a1b2c3d4 entrevista
"""

import sys
from kanban_store import KanbanBoard, FASES, FASE_LABEL


def cmd_list(board: KanbanBoard, fase: str = None):
    fases_a_mostrar = [fase] if fase else FASES
    for f in fases_a_mostrar:
        if f not in FASES:
            print(f"Fase desconhecida: {f}")
            print(f"Fases validas: {', '.join(FASES)}")
            return
        cards = board.by_fase(f)
        print(f"\n{FASE_LABEL[f]} ({len(cards)})")
        print("-" * 60)
        if not cards:
            print("  (vazio)")
        for c in cards:
            print(f"  [{c['id'][:8]}] {c['title'][:45]:<45} {c['company'][:20]}")
            if c.get("notas"):
                for linha in c["notas"].splitlines():
                    print(f"           📝 {linha}")


def cmd_move(board: KanbanBoard, job_id: str, fase: str, nota: str = ""):
    card = board.move(job_id, fase, nota)
    if not card:
        print(f"Vaga nao encontrada ou prefixo ambiguo: {job_id!r}")
        print("Use 'python3 kanban_cli.py list' para ver os IDs.")
        sys.exit(1)
    print(f"✓ {card['title']} → {FASE_LABEL[fase]}")


def cmd_note(board: KanbanBoard, job_id: str, nota: str):
    card = board.add_note(job_id, nota)
    if not card:
        print(f"Vaga nao encontrada ou prefixo ambiguo: {job_id!r}")
        sys.exit(1)
    print(f"✓ Nota adicionada em {card['title']}")


def cmd_fases():
    print("Fases disponiveis:")
    for f in FASES:
        print(f"  {f:<14} {FASE_LABEL[f]}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    board = KanbanBoard()
    cmd = args[0]

    if cmd == "list":
        cmd_list(board, args[1] if len(args) > 1 else None)
    elif cmd == "move":
        if len(args) < 3:
            print("Uso: kanban_cli.py move <job_id> <fase> [nota]")
            sys.exit(1)
        cmd_move(board, args[1], args[2], args[3] if len(args) > 3 else "")
    elif cmd == "note":
        if len(args) < 3:
            print("Uso: kanban_cli.py note <job_id> <texto>")
            sys.exit(1)
        cmd_note(board, args[1], " ".join(args[2:]))
    elif cmd == "fases":
        cmd_fases()
    else:
        print(f"Comando desconhecido: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
