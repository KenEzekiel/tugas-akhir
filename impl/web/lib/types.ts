export interface ContractResult {
  id: string
  name: string
  symbol: string
  description: string
  platform: string
  language: string
  license: string
  created: string
  verified: boolean
  tags: string[]
  externalUrl?: string
  address?: string
}
