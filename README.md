# second-brain-site

Projeção **pública** e gerada do Second Brain, servida por GitHub Pages em
<https://gitzambrano.github.io/second-brain-site/>.

Nada aqui é escrito à mão. Tudo é produzido por
`scripts/build_site.py` no repositório
[`second-brain-engine`](https://github.com/gitzambrano/second-brain-engine), a
partir da wiki privada.

```text
index.html          catálogo de todos os ensaios
essays/             os ensaios legíveis, renderizados
graph.html          mapa de conexões da base
sphere.html         o mesmo mapa, em globo
graph.json          dados do mapa
search-index.json   índice de busca do catálogo
assets/             CSS, JS e imagens referenciadas
```

## O que é público aqui

O catálogo e o mapa cobrem a base inteira: título, resumo, tags, datas, status
e conexões de cada ensaio, conceito, entidade e referência. **O corpo do texto**
só é publicado para os ensaios marcados `visibility: public`; os demais
aparecem com o selo *privado* e não abrem.

Um site estático não esconde o que serve — títulos e resumos aqui são legíveis
por qualquer pessoa, e essa é uma escolha deliberada. O que nunca sai do
repositório privado é o corpo das páginas não publicadas, qualquer caminho
para dentro dele e qualquer link que abra uma página não autorizada. Isso é
verificado a cada build por `scripts/check_site_privacy.py`.

## Para regenerar

```bash
python scripts/build_site.py
python scripts/build_site.py --check
python scripts/check_site_privacy.py
```

Não edite arquivos aqui: o próximo build sobrescreve.
