/* Receita analítica: UI compartilhada por imagem, lote e sequência. */
(() => {
  const labels = {
    pooling: {mean:'Média', max:'Máximo', median:'Mediana'},
    normalization: {l2:'L2', l1:'L1', linf:'L∞', none:'Sem normalização'},
    metric: {cosine:'Cosseno', euclidean:'Distância euclidiana', dot:'Produto escalar'}
  };
  const defaults = {version:1, pooling:'mean', normalization:'l2', metric:'cosine'};
  const explanations = {
    pooling: {
      mean:'Para cada coordenada, calcula a média dos valores de todos os tokens.',
      max:'Para cada coordenada, escolhe o maior valor entre todos os tokens. Não é o maior valor absoluto nem a maior barra do vetor médio.',
      median:'Para cada coordenada, escolhe o valor central entre os tokens; se a quantidade for par, usa a média dos dois centrais.'
    },
    normalization: {
      l2:'Divide todas as coordenadas pela raiz da soma dos quadrados. O comprimento L2 passa a ser 1.',
      l1:'Divide todas as coordenadas pela soma dos valores absolutos. Essa soma passa a ser 1.',
      linf:'Divide todas as coordenadas pelo maior valor absoluto. A maior magnitude passa a ser 1.',
      none:'Mantém os valores da agregação, inclusive o comprimento do vetor. O cosseno ainda considera os comprimentos na sua própria fórmula.'
    },
    metric: {
      cosine:'Compara direções. Valores maiores indicam maior proximidade; o resultado não é uma porcentagem de semelhança.',
      euclidean:'Mede a distância entre os vetores. Valores menores indicam maior proximidade; a normalização escolhida pode mudar o resultado.',
      dot:'Soma os produtos das coordenadas correspondentes. Valores maiores ficam primeiro; o resultado depende da direção e dos comprimentos e não fica limitado a −1 e 1.'
    }
  };
  class LabRecipe {
    constructor(element, {mode='single', apply=null}={}) {
      this.element=element;this.mode=mode;this.apply=apply;this.lastApplied=null;this.state='empty';this.busy=false;
      element.classList.add('recipe-panel');
      element.innerHTML=`<div class="recipe-heading"><h3>Escolha como analisar</h3><span class="badge">Metodologia da bancada</span></div>
        <p class="small">Estas escolhas atuam sobre as saídas do encoder. Os pesos e o merger aprendido do Qwen permanecem os mesmos. Abra uma etapa por vez.</p>
        <div class="recipe-steps"></div><p class="recipe-summary"></p><p class="recipe-context" role="status" aria-live="polite"></p>
        <button type="button" class="secondary recipe-apply hidden">Recalcular análise com os tokens salvos</button>`;
      this.fields={};this.steps=[];
      ['pooling','normalization','metric'].forEach((field,i)=>{
        const details=document.createElement('details');details.open=i===0;
        const id=element.id+'-'+field;
        details.innerHTML=`<summary>${i+1}. ${['Como resumir os tokens','Como normalizar','Como comparar'][i]} <span class="recipe-choice"></span></summary>
          <div class="recipe-step"><label for="${id}">${['Agregação por coordenada','Normalização do vetor','Medida de comparação'][i]}</label>
          <select id="${id}"></select><p class="small recipe-explanation"></p></div>`;
        const select=details.querySelector('select');
        for(const [value,label] of Object.entries(labels[field])){const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option)}
        select.value=defaults[field];this.fields[field]=select;this.steps.push(details);
        select.onchange=()=>{this.refresh();this.element.dispatchEvent(new CustomEvent('recipechange'))};
        if(i===1){const note=document.createElement('p');note.className='small recipe-direction';note.textContent='L1, L2 e L∞ preservam a direção de um vetor não nulo. Com cosseno, trocar apenas entre elas não muda matematicamente a comparação, embora mude as barras. Podem existir pequenas diferenças numéricas. Uma coordenada dominante não deixa de ser dominante por essa troca.';details.querySelector('.recipe-step').append(note)}
        if(i<2){const next=document.createElement('button');next.type='button';next.className='secondary recipe-next';next.textContent=['Continuar: normalização','Continuar: comparação'][i];next.onclick=()=>{details.open=false;this.steps[i+1].open=true;this.steps[i+1].querySelector('select').focus()};details.querySelector('.recipe-step').append(next)}
        details.ontoggle=()=>{if(details.open)for(const sibling of this.steps)if(sibling!==details)sibling.open=false};
        element.querySelector('.recipe-steps').append(details);
      });
      element.querySelector('.recipe-apply').onclick=async()=>{
        if(!this.apply)return;
        try{await this.apply(this.value())}catch(error){this.element.querySelector('.recipe-context').textContent=error.message}
      };
      this.refresh();
    }
    value(){return {version:1,...Object.fromEntries(Object.entries(this.fields).map(([name,select])=>[name,select.value]))}}
    set(value){for(const [name,select] of Object.entries(this.fields))select.value=value[name]||defaults[name];this.refresh()}
    applied(value){this.lastApplied={...value};this.state='ready';this.refresh()}
    availability(state,busy=this.busy){this.state=state;this.busy=busy;this.refresh()}
    setBusy(value){this.busy=value;this.refresh()}
    refresh(){
      const r=this.value();
      for(const [i,field] of ['pooling','normalization','metric'].entries()){
        this.fields[field].disabled=this.busy;
        this.steps[i].querySelector('.recipe-choice').textContent=labels[field][r[field]];
        this.steps[i].querySelector('.recipe-explanation').textContent=explanations[field][r[field]];
      }
      this.element.querySelector('.recipe-summary').textContent='Receita escolhida: '+LabRecipe.describe(r);
      let message;
      if(this.mode==='batch'){
        message=this.busy?'Receita fixada para o lote em execução. Todas as imagens usam estas mesmas escolhas.':'A receita será fixada ao iniciar o lote e salva com os resultados. Para mudar a agregação deste lote depois, será necessário executar um novo lote; os tokens completos não são guardados aqui.';
      }else if(this.state==='ready'){
        const changed=this.lastApplied&&JSON.stringify(r)!==JSON.stringify(this.lastApplied);
        message=(changed?'Os resultados ainda usam '+LabRecipe.describe(this.lastApplied)+'. ':'')+'Reutiliza os tokens salvos. Recalcular a análise não prepara a entrada nem executa o encoder novamente.';
        if(this.mode==='single')message+=' A medida de comparação será usada nos vizinhos dos lotes; sozinha, ela não muda este gráfico de uma imagem.';
      }else if(this.state==='dirty')message='A entrada mudou: precisa preparar novamente e executar o encoder. Os resultados anteriores não representam esta nova entrada.';
      else message='A receita será aplicada após executar o encoder. Depois, os tokens completos poderão ser reutilizados para outras escolhas.';
      this.element.querySelector('.recipe-context').textContent=message;
      const button=this.element.querySelector('.recipe-apply');button.classList.toggle('hidden',this.mode==='batch'||this.state!=='ready');button.disabled=this.busy;
    }
    static describe(r){return ['pooling','normalization','metric'].map(k=>labels[k][r[k]]).join(' → ')}
  }
  window.LabRecipe=LabRecipe;
})();
