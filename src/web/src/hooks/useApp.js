import { useContext } from 'react';
import { AppContext } from '../AppContext';

export const useApp = () => useContext(AppContext);
