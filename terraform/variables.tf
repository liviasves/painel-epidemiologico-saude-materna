variable "aiven_api_token" {
  description = "Token de API da Aiven (gerado no perfil do usuário)"
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Nome do projeto na Aiven"
  type        = string
}

variable "service_name" {
  description = "Nome do serviço PostgreSQL"
  type        = string
  default     = "pg-saude-materna"
}

variable "plan" {
  description = "Plano do serviço: gratuito (1 CPU, 1 GB RAM, 1 GB de armazenamento)"
  type        = string
  default     = "free-1-1gb"
}

variable "cloud_name" {
  description = "Nuvem/região. No plano gratuito fica nulo e a Aiven escolhe."
  type        = string
  default     = null
}
