output "host" {
  description = "Endereço do servidor PostgreSQL"
  value       = aiven_pg.banco.service_host
}

output "porta" {
  description = "Porta de conexão"
  value       = aiven_pg.banco.service_port
}

output "plano" {
  description = "Plano contratado (deve ser o gratuito)"
  value       = aiven_pg.banco.plan
}

# Contém usuário e senha: marcado como sensível, não aparece no terminal
output "uri_conexao" {
  description = "URI de conexão completa (usada pelo script de carga via .env)"
  value       = aiven_pg.banco.service_uri
  sensitive   = true
}
