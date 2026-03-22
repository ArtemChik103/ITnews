import { Outlet, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  IconButton,
  useMediaQuery,
  Drawer,
  useTheme,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import HomeIcon from '@mui/icons-material/Home';
import { useState } from 'react';
import SearchChatPanel from './SearchChatPanel';
import type { GraphEdge, SearchEntity } from '../types';

interface Props {
  onGraphUpdate?: (edges: GraphEdge[], entities: SearchEntity[]) => void;
}

const DRAWER_WIDTH = 380;

export default function Layout({ onGraphUpdate }: Props) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();

  const chatPanel = (
    <Box sx={{ width: isMobile ? '85vw' : DRAWER_WIDTH, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <SearchChatPanel
        onGraphUpdate={onGraphUpdate}
        onSourceClick={(id) => {
          navigate(`/articles/${id}`);
          if (isMobile) setDrawerOpen(false);
        }}
      />
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar variant="dense" sx={{ gap: 1 }}>
          {isMobile && (
            <IconButton
              edge="start"
              aria-label="Открыть чат"
              onClick={() => setDrawerOpen(true)}
            >
              <MenuIcon />
            </IconButton>
          )}
          <IconButton aria-label="На главную" onClick={() => navigate('/')}>
            <HomeIcon />
          </IconButton>
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
            📰 IT News Platform
          </Typography>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {isMobile ? (
          <Drawer
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            ModalProps={{ keepMounted: true }}
            sx={{ '& .MuiDrawer-paper': { bgcolor: 'background.default' } }}
          >
            {chatPanel}
          </Drawer>
        ) : (
          <Box sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            borderRight: 1,
            borderColor: 'divider',
            overflow: 'hidden',
            display: 'flex',
          }}>
            {chatPanel}
          </Box>
        )}

        <Box sx={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
