import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  type SelectChangeEvent,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import { useFilterStore } from '../store/useFilterStore';

const SOURCES = ['TechCrunch', 'Wired', 'Ars Technica', 'NewsAPI'];
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Русский' },
];

export default function FilterPanel() {
  const {
    source, language, dateFrom, dateTo, sort,
    setFilter, resetFilters,
  } = useFilterStore();

  const hasActiveFilters = source || language || dateFrom || dateTo;

  return (
    <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', p: 1.5 }}>
      <FilterListIcon sx={{ color: 'text.secondary' }} />

      <FormControl size="small" sx={{ minWidth: 130 }}>
        <InputLabel id="source-filter-label">Источник</InputLabel>
        <Select
          labelId="source-filter-label"
          value={source}
          label="Источник"
          onChange={(e: SelectChangeEvent) => setFilter('source', e.target.value)}
        >
          <MenuItem value="">Все</MenuItem>
          {SOURCES.map((s) => (
            <MenuItem key={s} value={s}>{s}</MenuItem>
          ))}
        </Select>
      </FormControl>

      <FormControl size="small" sx={{ minWidth: 110 }}>
        <InputLabel id="language-filter-label">Язык</InputLabel>
        <Select
          labelId="language-filter-label"
          value={language}
          label="Язык"
          onChange={(e: SelectChangeEvent) => setFilter('language', e.target.value)}
        >
          <MenuItem value="">Все</MenuItem>
          {LANGUAGES.map((l) => (
            <MenuItem key={l.value} value={l.value}>{l.label}</MenuItem>
          ))}
        </Select>
      </FormControl>

      <TextField
        type="date"
        size="small"
        label="От"
        value={dateFrom}
        onChange={(e) => setFilter('dateFrom', e.target.value)}
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { 'aria-label': 'Дата от' } }}
        sx={{ width: 150 }}
      />

      <TextField
        type="date"
        size="small"
        label="До"
        value={dateTo}
        onChange={(e) => setFilter('dateTo', e.target.value)}
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { 'aria-label': 'Дата до' } }}
        sx={{ width: 150 }}
      />

      <FormControl size="small" sx={{ minWidth: 120 }}>
        <InputLabel id="sort-filter-label">Сортировка</InputLabel>
        <Select
          labelId="sort-filter-label"
          value={sort}
          label="Сортировка"
          onChange={(e: SelectChangeEvent) => setFilter('sort', e.target.value as 'published_at' | 'ingested_at')}
        >
          <MenuItem value="published_at">По дате</MenuItem>
          <MenuItem value="ingested_at">По добавлению</MenuItem>
        </Select>
      </FormControl>

      {hasActiveFilters && (
        <Button
          size="small"
          startIcon={<ClearIcon />}
          onClick={resetFilters}
          aria-label="Сбросить все фильтры"
        >
          Сбросить
        </Button>
      )}
    </Box>
  );
}
