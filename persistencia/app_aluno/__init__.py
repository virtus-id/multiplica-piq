"""Adaptadores de persistência desta feature (`app-aluno`) — schema dedicado
`piq_app_aluno`, separado de `piq_motor_calculo` (NFR de segurança).

Cobre só o que é desta feature: respostas de coleta, contas, estado do caso,
itens repetidos, fila de revisão, consentimentos e eventos do caso — nunca
snapshot (a única porta de escrita de snapshot é
`engine.portas.RepositorioSnapshots`, implementada em `persistencia/supabase/
repositorio_snapshots.py`, RF-19/AC-43). Ver `persistencia/supabase/
migracoes/002_app_aluno.sql` (T-21).
"""
