export interface ContractResult {
  id: string
  name: string
  symbol: string
  description: string
  license: string
  created: string
  verified: boolean
  tags: string[]
  externalUrl?: string
  address?: string
  storage_protocol?: string
  storage_address?: string
  experimental?: boolean
  solc_version?: string
  verified_source?: boolean
  verified_source_code?: string
  functionality?: string
  domain?: string
  security_risks?: string[]
  similarity_score?: number
  // last_updated?: string
}
