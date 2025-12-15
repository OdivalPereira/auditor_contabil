# Guia de Implantação (Deploy) - Cont.AI

Este guia detalha como implantar (deploy) a aplicação Cont.AI usando Docker.

## Pré-requisitos

1.  **Docker** e **Docker Compose** instalados no servidor.
2.  Acesso ao código fonte (este repositório).

## Configuração

1.  **Credenciais**:
    *   Edite `config/auth.yaml` para definir as senhas iniciais de produção.
    *   **IMPORTANTE**: Mude a `cookie:key` para uma chave secreta e única.

2.  **Porta**:
    *   Por padrão, a aplicação roda na porta `8501`.
    *   Para mudar, altere o arquivo `docker-compose.yml`:
        ```yaml
        ports:
          - "80:8501"  # Exemplo: Acessar na porta 80
        ```

3.  **Persistência**:
    *   O `docker-compose.yml` já configura volumes para persistir dados importantes:
        *   `./data`: Histórico de usuários
        *   `./logs`: Logs de atividades
        *   `./config`: Arquivos de configuração

## Executando (Produção)

No terminal, na pasta raiz do projeto:

```bash
# Construir e iniciar os containers em modo "detached" (background)
docker-compose up -d --build
```

### Comandos Úteis

*   **Verificar status**: `docker-compose ps`
*   **Ver logs em tempo real**: `docker-compose logs -f`
*   **Parar aplicação**: `docker-compose down`
*   **Reiniciar**: `docker-compose restart`

## Manutenção

### Atualizações
Para atualizar a aplicação com novas versões do código:

```bash
git pull origin main
docker-compose up -d --build
```

### Monitoramento
Acesse a aba **Admin** dentro da aplicação (usuário `admin`) para ver:
*   Atividades recentes
*   Estatísticas de uso
*   Erros de processamento

Os logs brutos do container também podem ser acessados via `docker logs contai_auditor`.

## Troubleshooting

**O container não sobe ou cai logo em seguida?**
Verifique os logs:
```bash
docker-compose logs --tail=50
```

**Erro de "Out of Memory"?**
Verifique se a máquina tem memória suficiente (recomendado 2GB+ para OCR). Aumente limite no Docker se necessário.
