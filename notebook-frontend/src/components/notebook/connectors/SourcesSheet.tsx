import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { FormsPosthog, FormsDbt, FormsClickhouse, FormsSnowflake, FormsLooker, FormsAmplitude, FormsRedshift} from './forms'

interface DataSource {
  id: string;
  name: string;
  available: boolean;
  icon: string;
  form: React.ReactNode;
}

interface SourcesSheetProps {
  posthogSetup: (user_id: string, apiKey: string, baseUrl: string) => void;
}

export function SourcesSheet({ posthogSetup }: SourcesSheetProps) {
  const [dataSources] = useState<DataSource[]>([
    { id: 'posthog', name: 'PostHog', available: true, icon: `https://img.logo.dev/posthog.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsPosthog posthogSetup={posthogSetup} /> },
    { id: 'dbt', name: 'dbt', available: false, icon: `https://img.logo.dev/dbt.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsDbt /> },
    { id: 'clickhouse', name: 'ClickHouse', available: false, icon: `https://img.logo.dev/clickhouse.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsClickhouse /> },
    { id: 'snowflake', name: 'Snowflake', available: false, icon: `https://img.logo.dev/snowflake.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsSnowflake /> },
    { id: 'looker', name: 'Looker', available: false, icon: `https://img.logo.dev/looker.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsLooker /> },
    { id: 'amplitude', name: 'Amplitude', available: false, icon: `https://img.logo.dev/amplitude.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsAmplitude /> },
    { id: 'redshift', name: 'Redshift', available: false, icon: `https://img.logo.dev/aws.com?token=${process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN}&retina=true`, form: <FormsRedshift /> },

  ]);

  const [selectedSource, setSelectedSource] = useState<string | null>(null);

  const handleReset = () => setSelectedSource(null);

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Add Data Source
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[35vw] sm:max-w-[35vw]">
        <div className="py-1">
          {selectedSource ? (
            <>
              <Button variant="ghost" onClick={handleReset} className="mb-4">
                ← Back to sources
              </Button>
              {dataSources.find(source => source.id === selectedSource)?.form}
            </>
          ) : (
            <>
              <SheetHeader>
                <SheetTitle>Choose a Data Source</SheetTitle>
              </SheetHeader>
              <div className="grid grid-cols-3 gap-4 py-4">
                {dataSources.map((source) => (
                  <Button
                    key={source.id}
                    variant="outline"
                    className={`flex-col h-24 space-y-2 ${!source.available && 'opacity-50 cursor-not-allowed'}`}
                    disabled={!source.available}
                    onClick={() => source.available && setSelectedSource(source.id)}
                  >
                    <img src={source.icon} alt={source.name} className="h-8 w-8" />
                    <span>{source.name}</span>
                  </Button>
                ))}

                <div className="col-span-3 border-t pt-4">
                  <Button variant="ghost" className="w-full justify-start text-muted-foreground">
                    <span className="text-sm">Don't see what you need? Email us to suggest an integration</span>
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
