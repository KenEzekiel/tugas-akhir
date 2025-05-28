"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Copy, Check, Code, FileJson, Activity } from "lucide-react"
import { ImportContract } from "@/components/import-contract"
import { AddressBadge } from "@/components/address-badge"

interface ContractDetailsProps {
  contract: any
  onBack: () => void
}

export function ContractDetails({ contract, onBack }: ContractDetailsProps) {
  const [activeTab, setActiveTab] = useState("code")
  const [copied, setCopied] = useState(false)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <Button variant="outline" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
          <span className="sr-only">Back to results</span>
        </Button>
        <h2 className="text-2xl font-bold">{contract.name}</h2>
        {contract.verified && <Badge variant="default">Verified</Badge>}
        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const address = contract.deployments?.[0]?.address || "0x1234567890123456789012345678901234567890"
              navigator.clipboard.writeText(address)
              setCopied(true)
              setTimeout(() => setCopied(false), 2000)
            }}
            className="flex items-center gap-1"
          >
            {copied ? (
              <span className="flex items-center gap-1">
                <Check className="h-3.5 w-3.5" />
                Copied
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Copy className="h-3.5 w-3.5" />
                Copy Address
              </span>
            )}
          </Button>
          <ImportContract
            contract={{
              name: contract.name,
              address: contract.deployments?.[0]?.address || "0x1234567890123456789012345678901234567890",
              abi: contract.abi || [],
            }}
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contract Details</CardTitle>
          <CardDescription>{contract.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">License</h4>
              <p>{contract.license || "MIT"}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Created</h4>
              <p>{contract.created || "May 15, 2023"}</p>
            </div>
          </div>

          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Tags</h4>
            <div className="flex flex-wrap gap-2">
              {contract.tags.map((tag: string, i: number) => (
                <Badge key={i} variant="secondary">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>

          {contract.deployments && contract.deployments.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Deployments</h4>
              <div className="space-y-2">
                {contract.deployments.map((deployment: any, i: number) => (
                  <div
                    key={i}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-md"
                  >
                    <div>
                      <div className="font-medium">{deployment.network}</div>
                      <AddressBadge address={deployment.address} network={deployment.network} />
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-2 sm:mt-0">
                      {new Date(deployment.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="code" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Source Code
          </TabsTrigger>
          <TabsTrigger value="abi" className="flex items-center gap-2">
            <FileJson className="h-4 w-4" />
            ABI
          </TabsTrigger>
          <TabsTrigger value="activity" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Activity
          </TabsTrigger>
        </TabsList>

        <TabsContent value="code" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-lg">Source Code</CardTitle>
                <Button variant="outline" size="sm" onClick={() => copyToClipboard(contract.verified_source_code)} className="h-8">
                  {copied ? (
                    <span className="flex items-center gap-1">
                      <Check className="h-4 w-4" />
                      Copied
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Copy className="h-4 w-4" />
                      Copy
                    </span>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono">
                {contract.verified_source_code}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="abi" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-lg">ABI</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(JSON.stringify(contract.abi, null, 2))}
                  className="h-8"
                >
                  {copied ? (
                    <span className="flex items-center gap-1">
                      <Check className="h-4 w-4" />
                      Copied
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Copy className="h-4 w-4" />
                      Copy
                    </span>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono">
                {JSON.stringify(contract.abi, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Recent Activity</CardTitle>
              <CardDescription>Recent transactions and events</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Activity className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">No recent activity</h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  This contract has no recent activity or transaction data is not available
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
