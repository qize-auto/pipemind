import { Handle, Position } from 'reactflow';
import { useState } from 'react';
import { useI18n } from '../i18n';

export function ConditionNode({ data, selected, id }) {
  const { t } = useI18n();
  const [condition, setCondition] = useState(data.condition || '');
  const [operator, setOperator] = useState(data.operator || 'contains');
  const [compareValue, setCompareValue] = useState(data.compareValue || '');

  data.condition = condition;
  data.operator = operator;
  data.compareValue = compareValue;

  const verdict = data.verdict;
  const verdictColor = verdict === true ? 'emerald' : verdict === false ? 'red' : 'gray';

  return (
    <div className={`min-w-[240px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-amber-400 ring-2 ring-amber-400/20' : (data.error ? 'node-error' : 'border-amber-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}
    style={{ clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)', padding: '2px', background: 'none' }}
    >
      <div className="rounded-none bg-gray-900/95 p-3" style={{ clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)', minHeight: '260px', display: 'flex', flexDirection: 'column' }}>
        {/* Input handle - left */}
        <Handle type="target" position={Position.Left} id="input-left" className="!bg-amber-400 !w-3 !h-3 !border-2 !border-gray-900" style={{ left: -8, top: '50%' }} />
        {/* Input handle - top */}
        <Handle type="target" position={Position.Top} id="input-top" className="!bg-amber-400 !w-3 !h-3 !border-2 !border-gray-900" style={{ left: '50%', top: -8 }} />

        <div className="flex items-center justify-center gap-1 mt-4 mb-2">
          <span className="text-sm">🔀</span>
          <span className="text-sm font-medium text-amber-300">{t('node.condition')}</span>
        </div>

        <div className="px-2 space-y-1.5 flex-1">
          <input
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            placeholder={t('node.condition.placeholder')}
            className="w-full px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-500/50"
          />

          <select
            value={operator}
            onChange={(e) => setOperator(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-300 focus:outline-none"
          >
            <option value="contains">{t('condition.contains')}</option>
            <option value="equals">{t('condition.equals')}</option>
            <option value="length_gt">{t('condition.length_gt')}</option>
            <option value="length_lt">{t('condition.length_lt')}</option>
            <option value="regex">{t('condition.regex')}</option>
          </select>

          <input
            value={compareValue}
            onChange={(e) => setCompareValue(e.target.value)}
            placeholder={t('node.condition.compare')}
            className="w-full px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-500/50"
          />
        </div>

        {(verdict === true || verdict === false) && (
          <div className={`mt-1 px-2 py-1 text-xs text-center rounded ${
            verdict === true ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'
          }`}>
            {verdict === true ? '✅ true' : '❌ false'}
          </div>
        )}

        {data.error && (
          <div className="mt-1 px-2 py-1 text-xs text-center text-red-400 bg-red-500/10 rounded">❌ {String(data.error).slice(0, 40)}</div>
        )}

        {/* Output handle - right (true) */}
        <Handle type="source" position={Position.Right} id="true" className="!bg-emerald-400 !w-3 !h-3 !border-2 !border-gray-900" style={{ right: -8, top: '35%' }}>
          <div style={{ position: 'absolute', left: 14, top: -2, fontSize: 9, color: '#6ee7b7', whiteSpace: 'nowrap' }}>true</div>
        </Handle>

        {/* Output handle - bottom (false) */}
        <Handle type="source" position={Position.Bottom} id="false" className="!bg-red-400 !w-3 !h-3 !border-2 !border-gray-900" style={{ left: '50%', bottom: -8 }}>
          <div style={{ position: 'absolute', top: 12, left: -2, fontSize: 9, color: '#fca5a5', whiteSpace: 'nowrap' }}>false</div>
        </Handle>
      </div>
    </div>
  );
}
