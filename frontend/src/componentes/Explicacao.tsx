/**
 * O ícone ⓘ de ajuda dos campos numéricos da ficha de dívida — `RF-562`
 * (T-664 a T-679).
 *
 * **Um único `aberto`, nunca dois estados independentes.** Hover, foco,
 * toque e clique todos abrem; `mouseleave`, `blur`, `Esc` e clique/toque
 * fora todos fecham. Nenhum deles faz um toggle — se o clique alternasse o
 * estado, um clique que também dispara `focus` (como é o caso do mouse)
 * abriria e fecharia no mesmo gesto. É a mesma armadilha que
 * `plans/app-aluno.plan.md` (`R20.10`) nomeia e que esta escolha evita.
 *
 * **Nunca modal.** O balão é `role="tooltip"`, sem foco próprio e sem
 * capturar o foco do campo ao lado — ele só aparece/desaparece; o aluno
 * continua podendo preencher o campo com o balão aberto.
 *
 * Sem biblioteca: poucas linhas de `useState`/`useEffect`, mesma política de
 * `Icone.tsx` ("são oito `path`, escritos aqui" — não uma dependência nova
 * para isto).
 */
import type { KeyboardEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'

import Icone from './Icone'

interface ExplicacaoProps {
  /** Nome do campo, para o rótulo acessível ("O que é Saldo devedor?"). */
  campo: string
  oQueE: string
  ondeEncontrar: string
}

export default function Explicacao({ campo, oQueE, ondeEncontrar }: ExplicacaoProps) {
  const [aberto, setAberto] = useState(false)
  const containerRef = useRef<HTMLSpanElement>(null)
  const botaoRef = useRef<HTMLButtonElement>(null)
  const idBalao = useId()

  // Clique/toque FORA do botão e do balão fecha (`EC-99`) — checagem própria,
  // independente do `blur` do botão (que já cobre o caso de o foco mudar
  // para outro controle focável).
  useEffect(() => {
    if (!aberto) return
    function aoInteragirFora(evento: MouseEvent | TouchEvent) {
      if (!containerRef.current?.contains(evento.target as Node)) setAberto(false)
    }
    document.addEventListener('mousedown', aoInteragirFora)
    document.addEventListener('touchstart', aoInteragirFora)
    return () => {
      document.removeEventListener('mousedown', aoInteragirFora)
      document.removeEventListener('touchstart', aoInteragirFora)
    }
  }, [aberto])

  function aoTeclar(evento: KeyboardEvent<HTMLButtonElement>) {
    if (evento.key !== 'Escape') return
    setAberto(false)
    botaoRef.current?.focus()
  }

  return (
    <span ref={containerRef} className="relative inline-flex">
      <button
        ref={botaoRef}
        type="button"
        className="inline-flex h-7 w-7 items-center justify-center rounded-full text-accent hover:bg-accent-soft"
        aria-label={`O que é ${campo}?`}
        aria-expanded={aberto}
        aria-describedby={idBalao}
        onMouseEnter={() => setAberto(true)}
        onMouseLeave={() => setAberto(false)}
        onFocus={() => setAberto(true)}
        onBlur={() => setAberto(false)}
        onClick={() => setAberto(true)}
        onTouchStart={() => setAberto(true)}
        onKeyDown={aoTeclar}
      >
        <Icone nome="duvida" className="h-4 w-4" />
      </button>
      {aberto && (
        <span
          id={idBalao}
          role="tooltip"
          className="cartao absolute left-0 top-full z-10 mt-2 w-64 text-left text-[0.95rem] font-normal"
        >
          <strong className="block">{oQueE}</strong>
          <span className="nota block">{ondeEncontrar}</span>
        </span>
      )}
    </span>
  )
}
