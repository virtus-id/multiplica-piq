/**
 * O plano do aluno deficitário — `RF-468`, `RF-469`, `RF-453` (`T-437`).
 *
 * Quando o mês fecha no negativo, o aluno não recebe um cronograma: recebe um
 * plano PROVISÓRIO que manda estancar primeiro. Em ordem: o resultado do mês em
 * destaque e quanto falta para zerar; os maiores gastos que ele mesmo informou;
 * e a ordem de quitação como RECOMENDAÇÃO, sem prazo nem mês de quitação.
 *
 * **Todo texto e todo valor vêm do servidor, verbatim** (Lei nº 3): aqui não se
 * soma nem se formata nada. Os textos vêm de `estabilizacao_textos`; sem eles
 * (planos montados à mão em outros testes), o bloco usa só os números.
 */
import Icone from "./Icone";
import type { Plano } from "../tipos";

interface PlanoDoDeficitarioProps {
  plano: Plano;
}

function comValor(texto: string | undefined, valor: string): string {
  return (texto ?? "").replace("{valor}", valor);
}

export default function PlanoDoDeficitario({ plano }: PlanoDoDeficitarioProps) {
  const textos = plano.estabilizacao_textos ?? {};
  const gastos = plano.maiores_gastos ?? [];
  const mostrarOrdem = plano.ordem.length > 0;

  return (
    <>
      <section className="cartao" aria-labelledby="titulo-estancar">
        <h2 id="titulo-estancar" className="flex items-center gap-2">
          <Icone nome="conferencia" />
          {textos.titulo ?? "Primeiro, estancar o problema"}
        </h2>
        <div className="rounded-piq border-l-8 border-bad p-3" role="status">
          <span className="eyebrow block">
            {textos.resultado_rotulo ?? "Seu mês fecha em"}
          </span>
          <strong className="font-serif block text-3xl tabular-nums text-bad">
            {plano.RESULTADO_CAIXA_OBSERVADO}
          </strong>
        </div>
        <div className="aviso-atencao">
          <p className="m-0">
            {comValor(textos.texto, plano.RESULTADO_CAIXA_OBSERVADO)}
          </p>
          <p className="m-0 mt-2 font-bold">
            {comValor(textos.falta_cortar, plano.FALTA_CORTAR)}
          </p>
          {textos.depois_de_zerar && (
            <p className="m-0 mt-2">{textos.depois_de_zerar}</p>
          )}
        </div>
      </section>

      {gastos.length > 0 && (
        <section className="cartao" aria-labelledby="titulo-gastos">
          <h2 id="titulo-gastos" className="flex items-center gap-2">
            <Icone nome="dinheiro" />
            {textos.gastos_titulo}
          </h2>
          <p className="text-muted m-0">{textos.gastos_intro}</p>
          <dl className="m-0 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
            {gastos.map((gasto) => (
              <div key={`${gasto.nome}-${gasto.valor}`} className="contents">
                <dt>{gasto.nome}</dt>
                <dd className="m-0 font-bold tabular-nums text-bad">
                  {gasto.valor}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {mostrarOrdem && (
        <section className="cartao" aria-labelledby="titulo-ordem-provisoria">
          <h2 id="titulo-ordem-provisoria" className="flex items-center gap-2">
            <Icone nome="dinheiro" />
            {textos.ordem_titulo}
          </h2>
          <p className="text-muted m-0">{textos.ordem_intro}</p>
          {plano.metodo && (
            <p className="text-muted m-0 text-sm">
              {textos.metodo_rotulo}: {plano.metodo}
            </p>
          )}
          <ol className="lista list-none p-0">
            {plano.ordem.map((posicao) => (
              <li
                key={posicao.DIVIDA_ID}
                className="rounded-piq border border-line p-3"
              >
                <p className="m-0 font-bold">
                  {posicao.indice}. {posicao.nome}
                </p>
                {(posicao.fatos ?? []).length > 0 && (
                  <p className="text-muted m-0 text-sm">
                    {(posicao.fatos ?? [])
                      .map((fato) => `${fato.rotulo}: ${fato.valor}`)
                      .join(" · ")}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}
