"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Copy,
  Check,
  Code,
  Shield,
  Zap,
  Layers,
  Target,
  Tag,
} from "lucide-react";
import { ImportContract } from "@/components/import-contract";
import { AddressBadge } from "@/components/address-badge";
import { ContractResult } from "@/lib/types";

interface ContractDetailsProps {
  contract: ContractResult;
  onBack: () => void;
}

// Helper function to render attribute badges with icons
function AttributeBadges({
  items,
  icon: Icon,
  variant = "secondary" as const,
  maxItems = 5,
}: {
  items?: string[];
  icon: any;
  variant?: "default" | "secondary" | "destructive" | "outline";
  maxItems?: number;
}) {
  if (!items || items.length === 0) return null;

  const displayItems = items.slice(0, maxItems);
  const remainingCount = items.length - maxItems;

  return (
    <div className="flex flex-wrap gap-2">
      {displayItems.map((item, i) => (
        <Badge
          key={`${item}-${i}`}
          variant={variant}
          className="flex items-center gap-1"
        >
          <Icon className="h-3 w-3" />
          {item}
        </Badge>
      ))}
      {remainingCount > 0 && (
        <Badge variant="outline">+{remainingCount} more</Badge>
      )}
    </div>
  );
}

export function ContractDetails({ contract, onBack }: ContractDetailsProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <Button variant="outline" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
          <span className="sr-only">Back to results</span>
        </Button>
        <h2 className="text-2xl font-bold">{contract.name}</h2>
        {contract.verified && <Badge variant="default">Verified</Badge>}
        {contract.experimental && <Badge variant="outline">Experimental</Badge>}
        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const address =
                `0x${contract.storage_address}` ||
                "0x1234567890123456789012345678901234567890";
              navigator.clipboard.writeText(address);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
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
              address:
                `0x${contract.storage_address}` ||
                "0x1234567890123456789012345678901234567890",
            }}
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contract Details</CardTitle>
          <CardDescription>{contract.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                License
              </h4>
              <p>{contract.license || "MIT"}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Created
              </h4>
              <p>{contract.created || "May 15, 2023"}</p>
            </div>
            {contract.solc_version && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Solidity Version
                </h4>
                <p>{contract.solc_version}</p>
              </div>
            )}
            {contract.storage_protocol && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Storage Protocol
                </h4>
                <p>{contract.storage_protocol}</p>
              </div>
            )}
          </div>

          {/* Tags */}
          {contract.tags && contract.tags.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Tag className="h-4 w-4" />
                Tags
              </h4>
              <div className="flex flex-wrap gap-2">
                {contract.tags.map((tag: string, i: number) => (
                  <Badge key={i} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Domain */}
          {contract.domain && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Target className="h-4 w-4" />
                Application Domain
              </h4>
              <p className="text-sm">{contract.domain}</p>
            </div>
          )}

          {/* Standards */}
          {contract.standards && contract.standards.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Layers className="h-4 w-4" />
                Standards
              </h4>
              <AttributeBadges
                items={contract.standards}
                icon={Layers}
                variant="default"
              />
            </div>
          )}

          {/* Patterns */}
          {contract.patterns && contract.patterns.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Zap className="h-4 w-4" />
                Design Patterns
              </h4>
              <AttributeBadges
                items={contract.patterns}
                icon={Zap}
                variant="secondary"
              />
            </div>
          )}

          {/* Functionalities */}
          {contract.functionalities && contract.functionalities.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Zap className="h-4 w-4" />
                Functionalities
              </h4>
              <AttributeBadges
                items={contract.functionalities}
                icon={Zap}
                variant="secondary"
              />
            </div>
          )}

          {/* Security Risks */}
          {contract.security_risks && contract.security_risks.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                <Shield className="h-4 w-4" />
                Security Considerations
              </h4>
              <p className="text-sm">{contract.security_risks}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {contract.verified_source_code && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle className="text-lg flex items-center gap-2">
                <Code className="h-5 w-5" />
                Source Code
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  copyToClipboard(contract.verified_source_code || "")
                }
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
                    Copy Code
                  </span>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap">
              {contract.verified_source_code}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
